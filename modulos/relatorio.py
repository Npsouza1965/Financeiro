import streamlit as st
import sqlite3
import pandas as pd
import os
import io
from datetime import date, datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "nps_financeiro.db")
PASTA_RELATORIOS = "Relatorios"

# ----------------------------
# Funções de banco de dados
# ----------------------------
def conectar_db():
    return sqlite3.connect(DB_FILE)

def tabela_existe(conn, tabela="financeiro"):
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}';")
    return cursor.fetchone() is not None

# ----------------------------
# Funções auxiliares
# ----------------------------
def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_data_brasileira(data):
    """Formata data para formato brasileiro DD/MM/AAAA"""
    if isinstance(data, (datetime, pd.Timestamp)):
        return data.strftime("%d/%m/%Y")
    elif isinstance(data, date):
        return data.strftime("%d/%m/%Y")
    elif isinstance(data, str):
        try:
            # Tenta converter string para data
            data_obj = datetime.strptime(data, "%Y-%m-%d")
            return data_obj.strftime("%d/%m/%Y")
        except:
            return data
    return data

def carregar_dados_financeiros(data_inicio, data_fim, status_filtro="Todos"):
    """Carrega dados financeiros com filtros aplicados"""
    conn = conectar_db()
    
    if not tabela_existe(conn, "financeiro"):
        st.warning("A tabela 'financeiro' não existe no banco. Verifique o banco de dados.")
        conn.close()
        return pd.DataFrame()

    try:
        # Verificar quais colunas existem
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(financeiro)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        
        # Colunas base obrigatórias
        colunas_base = ["data", "valor"]
        
        # Verificar se as colunas base existem
        colunas_faltantes = [col for col in colunas_base if col not in colunas_existentes]
        if colunas_faltantes:
            st.error(f"Colunas obrigatórias faltando: {colunas_faltantes}")
            return pd.DataFrame()
        
        # Colunas opcionais - tentar diferentes nomes possíveis
        colunas_opcionais = []
        
        # Para categoria - tentar diferentes nomes
        possiveis_categorias = ["categoria", "classificacao", "classificação", "tipo"]
        categoria_encontrada = next((cat for cat in possiveis_categorias if cat in colunas_existentes), None)
        
        if categoria_encontrada:
            colunas_opcionais.append(categoria_encontrada)
        
        # Outras colunas opcionais
        outras_colunas = ["tipo", "grupo", "subgrupo", "plano", "descricao", "banco", "status", "entidade"]
        colunas_opcionais.extend([col for col in outras_colunas if col in colunas_existentes])
        
        # Selecionar todas as colunas disponíveis
        colunas_selecionar = colunas_base + colunas_opcionais
        
        # Construir query
        colunas_str = ", ".join(colunas_selecionar)
        query = f"SELECT {colunas_str} FROM financeiro WHERE data BETWEEN ? AND ?"
        
        params = [data_inicio, data_fim]
        
        if status_filtro != "Todos" and "status" in colunas_existentes:
            query += " AND status = ?"
            params.append(status_filtro)
        
        # Ordenação
        query += " ORDER BY data"
        if "grupo" in colunas_existentes:
            query += ", grupo"
        if "subgrupo" in colunas_existentes:
            query += ", subgrupo"
        if "plano" in colunas_existentes:
            query += ", plano"
        
        df = pd.read_sql_query(query, conn, params=params)
        
        # Determinar se é crédito ou débito
        if categoria_encontrada:
            # Usar a coluna de categoria encontrada
            df["CRÉDITO"] = df.apply(lambda x: x["valor"] if str(x[categoria_encontrada]).lower() == "crédito" else 0, axis=1)
            df["DÉBITO"] = df.apply(lambda x: x["valor"] if str(x[categoria_encontrada]).lower() == "débito" else 0, axis=1)
        else:
            # Se não há categoria, tentar determinar pelo valor (negativo = débito, positivo = crédito)
            df["CRÉDITO"] = df.apply(lambda x: x["valor"] if x["valor"] > 0 else 0, axis=1)
            df["DÉBITO"] = df.apply(lambda x: abs(x["valor"]) if x["valor"] < 0 else 0, axis=1)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# ----------------------------
# Relatório Analítico
# ----------------------------
def rel_analitico():
    st.header("📑 Relatório Analítico")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicio = st.date_input("Data inicial", value=date.today())
    with col2:
        data_fim = st.date_input("Data final", value=date.today())
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"])

    # Carregar dados
    with st.spinner("Carregando dados..."):
        df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # Processar dados
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    
    # Garantir que as colunas CRÉDITO e DÉBITO existem
    if "CRÉDITO" not in df.columns:
        df["CRÉDITO"] = 0
    if "DÉBITO" not in df.columns:
        df["DÉBITO"] = 0

    # Ordenar
    colunas_ordenacao = []
    if "grupo" in df.columns:
        colunas_ordenacao.append("grupo")
    if "subgrupo" in df.columns:
        colunas_ordenacao.append("subgrupo")
    if "plano" in df.columns:
        colunas_ordenacao.append("plano")
    if "data" in df.columns:
        colunas_ordenacao.append("data")
    
    if colunas_ordenacao:
        df = df.sort_values(by=colunas_ordenacao)

    # Totais
    total_credito = df["CRÉDITO"].sum()
    total_debito = df["DÉBITO"].sum()
    saldo = total_credito - total_debito

    # Exibir dados
    st.subheader("📊 Lançamentos Detalhados")
    
    # Formatar datas para exibição
    df_exibir = df.copy()
    if "data" in df_exibir.columns:
        df_exibir["data"] = df_exibir["data"].apply(formatar_data_brasileira)
    
    # Selecionar colunas para exibição
    colunas_exibicao = ["data", "grupo", "subgrupo", "plano", "descricao", "banco", "CRÉDITO", "DÉBITO"]
    colunas_disponiveis = [col for col in colunas_exibicao if col in df_exibir.columns]
    
    df_exibir = df_exibir[colunas_disponiveis]
    
    # Formatar colunas numéricas
    st.dataframe(
        df_exibir.style.format({
            "CRÉDITO": lambda x: formatar_moeda(x) if x > 0 else "",
            "DÉBITO": lambda x: formatar_moeda(x) if x > 0 else ""
        }),
        use_container_width=True,
        height=400
    )

    # Resumo
    st.subheader("💰 Resumo Financeiro")
    col_res1, col_res2, col_res3 = st.columns(3)
    with col_res1:
        st.metric("Total Créditos", formatar_moeda(total_credito))
    with col_res2:
        st.metric("Total Débitos", formatar_moeda(total_debito))
    with col_res3:
        st.metric("Saldo", formatar_moeda(saldo), delta=formatar_moeda(saldo))

    # Botão para gerar PDF
    if st.button("📄 Gerar PDF - Relatório Analítico", use_container_width=True):
        gerar_pdf_analitico(df, total_credito, total_debito, saldo, data_inicio, data_fim)

# ----------------------------
# Geração PDF Analítico
# ----------------------------
def gerar_pdf_analitico(df, total_credito, total_debito, saldo, data_inicio, data_fim):
    """Gera PDF do relatório analítico"""
    try:
        # Criar pasta de relatórios
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_pdf = os.path.join(PASTA_RELATORIOS, f"relatorio_analitico_{timestamp}.pdf")

        # Configurar PDF
        doc = SimpleDocTemplate(
            caminho_pdf, 
            pagesize=A4, 
            rightMargin=20, 
            leftMargin=20, 
            topMargin=20, 
            bottomMargin=20
        )
        elements = []

        # Estilos
        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        subtitulo_style = ParagraphStyle(
            'Subtitulo',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=9
        )

        # Título e período
        elements.append(Paragraph("RELATÓRIO ANALÍTICO FINANCEIRO", titulo_style))
        periodo_str = f"Período: {formatar_data_brasileira(data_inicio)} a {formatar_data_brasileira(data_fim)}"
        elements.append(Paragraph(periodo_str, subtitulo_style))

        # Preparar dados da tabela
        colunas = ["Data", "Grupo", "Descrição", "Crédito", "Débito"]
        dados = [colunas]

        for _, row in df.iterrows():
            data_str = formatar_data_brasileira(row["data"]) if "data" in df.columns else ""
            grupo_str = row["grupo"] if "grupo" in df.columns else ""
            descricao_str = row["descricao"] if "descricao" in df.columns else ""
            
            dados.append([
                data_str,
                grupo_str,
                descricao_str,
                formatar_moeda(row["CRÉDITO"]) if row["CRÉDITO"] > 0 else "",
                formatar_moeda(row["DÉBITO"]) if row["DÉBITO"] > 0 else ""
            ])

        # Criar tabela
        tabela = Table(dados, colWidths=[60, 80, 200, 70, 70])
        
        # Estilo da tabela
        estilo_tabela = TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ])

        tabela.setStyle(estilo_tabela)
        elements.append(tabela)

        # Resumo
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Total Créditos: {formatar_moeda(total_credito)}", normal_style))
        elements.append(Paragraph(f"Total Débitos: {formatar_moeda(total_debito)}", normal_style))
        elements.append(Paragraph(f"Saldo Final: {formatar_moeda(saldo)}", normal_style))

        # Data de geração
        elements.append(Spacer(1, 10))
        data_geracao = Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style)
        elements.append(data_geracao)

        # Gerar PDF
        doc.build(elements)
        st.success(f"✅ Relatório gerado com sucesso!")
        
        # Oferecer download
        with open(caminho_pdf, "rb") as f:
            pdf_data = f.read()
        
        st.download_button(
            label="⬇️ Baixar PDF",
            data=pdf_data,
            file_name=f"relatorio_analitico_{timestamp}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"❌ Erro ao gerar PDF: {e}")

# ----------------------------
# Relatório Sintético
# ----------------------------
def rel_sintetico():
    st.header("📊 Relatório Sintético")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicio = st.date_input("Data inicial", value=date(date.today().year, 1, 1), key="sintetico_inicio")
    with col2:
        data_fim = st.date_input("Data final", value=date.today(), key="sintetico_fim")
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="sintetico_status")

    # Carregar dados
    with st.spinner("Carregando dados..."):
        df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # Processar dados
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    
    # Garantir que as colunas CRÉDITO e DÉBITO existem
    if "CRÉDITO" not in df.columns:
        df["CRÉDITO"] = 0
    if "DÉBITO" not in df.columns:
        df["DÉBITO"] = 0

    # Agrupar dados - apenas se as colunas de agrupamento existirem
    colunas_agrupamento = []
    if "grupo" in df.columns:
        colunas_agrupamento.append("grupo")
    if "subgrupo" in df.columns:
        colunas_agrupamento.append("subgrupo")
    if "plano" in df.columns:
        colunas_agrupamento.append("plano")
    
    if colunas_agrupamento:
        agrupado = df.groupby(colunas_agrupamento, dropna=False).agg({
            "CRÉDITO": "sum",
            "DÉBITO": "sum"
        }).reset_index()
        
        agrupado = agrupado.sort_values(by=colunas_agrupamento)
    else:
        # Se não há colunas para agrupar, usar dados totais
        agrupado = pd.DataFrame({
            "Grupo": ["GERAL"],
            "CRÉDITO": [df["CRÉDITO"].sum()],
            "DÉBITO": [df["DÉBITO"].sum()]
        })

    # Calcular totais
    total_credito = agrupado["CRÉDITO"].sum()
    total_debito = agrupado["DÉBITO"].sum()
    saldo = total_credito - total_debito

    # Adicionar linha de totais
    linha_total = pd.DataFrame({
        "grupo": [""],
        "subgrupo": [""] if "subgrupo" in agrupado.columns else [""],
        "plano": [""] if "plano" in agrupado.columns else [""],
        "CRÉDITO": [total_credito],
        "DÉBITO": [total_debito]
    })
    
    # Ajustar nomes das colunas para concatenação
    if "subgrupo" not in linha_total.columns and "subgrupo" in agrupado.columns:
        linha_total["subgrupo"] = ""
    if "plano" not in linha_total.columns and "plano" in agrupado.columns:
        linha_total["plano"] = ""
    
    # Adicionar descrição para linha de total
    if len(colunas_agrupamento) > 0:
        linha_total[colunas_agrupamento[-1]] = "TOTAL GERAL"
    
    agrupado_final = pd.concat([agrupado, linha_total], ignore_index=True)

    # Exibir tabela
    st.subheader("📋 Resumo por Grupo/Subgrupo/Plano")
    st.dataframe(
        agrupado_final.style.format({
            "CRÉDITO": lambda x: formatar_moeda(x),
            "DÉBITO": lambda x: formatar_moeda(x)
        }),
        use_container_width=True,
        height=500
    )

    # Resumo financeiro
    st.subheader("💰 Resumo Financeiro")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Créditos", formatar_moeda(total_credito))
    with col2:
        st.metric("Total Débitos", formatar_moeda(total_debito))
    with col3:
        st.metric("Saldo", formatar_moeda(saldo), delta=formatar_moeda(saldo))

    # Botão para gerar PDF
    if st.button("📄 Gerar PDF - Relatório Sintético", use_container_width=True):
        gerar_pdf_sintetico(agrupado_final, total_credito, total_debito, saldo, data_inicio, data_fim)

# ----------------------------
# Geração PDF Sintético
# ----------------------------
def gerar_pdf_sintetico(agrupado_final, total_credito, total_debito, saldo, data_inicio, data_fim):
    """Gera PDF do relatório sintético"""
    try:
        # Criar pasta de relatórios
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_pdf = os.path.join(PASTA_RELATORIOS, f"relatorio_sintetico_{timestamp}.pdf")

        # Configurar PDF
        doc = SimpleDocTemplate(
            caminho_pdf, 
            pagesize=A4, 
            rightMargin=20, 
            leftMargin=20, 
            topMargin=20, 
            bottomMargin=20
        )
        elements = []

        # Estilos
        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        subtitulo_style = ParagraphStyle(
            'Subtitulo',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=20
        )

        # Título e período
        elements.append(Paragraph("RELATÓRIO SINTÉTICO FINANCEIRO", titulo_style))
        periodo_str = f"Período: {formatar_data_brasileira(data_inicio)} a {formatar_data_brasileira(data_fim)}"
        elements.append(Paragraph(periodo_str, subtitulo_style))

        # Preparar dados da tabela
        colunas = ["Grupo", "Subgrupo", "Plano", "Crédito", "Débito"]
        # Remover colunas que não existem no DataFrame
        colunas = [col for col in colunas if col.lower() in [c.lower() for c in agrupado_final.columns]]
        
        dados = [colunas]

        for _, row in agrupado_final.iterrows():
            linha = []
            for coluna in colunas:
                valor = row.get(coluna, row.get(coluna.lower(), ""))
                if coluna in ["Crédito", "Débito"]:
                    linha.append(formatar_moeda(valor))
                else:
                    linha.append(str(valor) if pd.notna(valor) else "")
            dados.append(linha)

        # Criar tabela
        largura_coluna = 400 / len(colunas)  # Distribuir igualmente
        col_widths = [largura_coluna] * len(colunas)
        
        tabela = Table(dados, colWidths=col_widths)
        
        # Estilo da tabela
        estilo_tabela = TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (-2, 1), (-1, -1), 'RIGHT'),  # Últimas 2 colunas alinhadas à direita
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ])

        tabela.setStyle(estilo_tabela)
        elements.append(tabela)

        # Resumo
        elements.append(Spacer(1, 20))
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10)
        elements.append(Paragraph(f"Total Créditos: {formatar_moeda(total_credito)}", normal_style))
        elements.append(Paragraph(f"Total Débitos: {formatar_moeda(total_debito)}", normal_style))
        elements.append(Paragraph(f"Saldo Final: {formatar_moeda(saldo)}", normal_style))

        # Data de geração
        elements.append(Spacer(1, 10))
        data_geracao = Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style)
        elements.append(data_geracao)

        # Gerar PDF
        doc.build(elements)
        st.success(f"✅ Relatório gerado com sucesso!")
        
        # Oferecer download
        with open(caminho_pdf, "rb") as f:
            pdf_data = f.read()
        
        st.download_button(
            label="⬇️ Baixar PDF",
            data=pdf_data,
            file_name=f"relatorio_sintetico_{timestamp}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"❌ Erro ao gerar PDF: {e}")

if __name__ == "__main__":
    st.title("📈 Sistema de Relatórios Financeiros")
    tab1, tab2 = st.tabs(["Relatório Analítico", "Relatório Sintético"])
    
    with tab1:
        rel_analitico()
    
    with tab2:
        rel_sintetico()