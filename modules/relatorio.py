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

DB_FILE = "financeiro.db"
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

def carregar_dados_financeiros(data_inicio, data_fim, status_filtro="Todos"):
    """Carrega dados financeiros com filtros aplicados"""
    conn = conectar_db()
    
    if not tabela_existe(conn, "financeiro"):
        st.warning("A tabela 'financeiro' não existe no banco. Verifique o banco de dados.")
        conn.close()
        return pd.DataFrame()

    # Query com todos os campos necessários
    query = """
        SELECT data, tipo, Grupo, subgrupo, plano, descricao, banco, 
               classificacao, valor, status, entidade
        FROM financeiro
        WHERE data BETWEEN ? AND ?
    """
    
    params = [data_inicio, data_fim]
    
    if status_filtro != "Todos":
        query += " AND status = ?"
        params.append(status_filtro)
    
    query += " ORDER BY data, Grupo, subgrupo, plano"
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    
    return df

# ----------------------------
# Relatório Analítico
# ----------------------------
def rel_analitico():
    st.header("📑 Relatório Analítico")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicio = st.date_input("Data inicial", value=date(date.today().year, 1, 1))
    with col2:
        data_fim = st.date_input("Data final", value=date.today())
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"])

    # Carregar dados
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # Processar dados
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    
    # Calcular créditos e débitos
    df["CRÉDITO"] = df.apply(lambda x: x["valor"] if x["classificacao"] == "Crédito" else 0, axis=1)
    df["DÉBITO"] = df.apply(lambda x: x["valor"] if x["classificacao"] == "Débito" else 0, axis=1)

    # Ordenar
    df = df.sort_values(by=["Grupo", "subgrupo", "plano", "data"])

    # Totais
    total_credito = df["CRÉDITO"].sum()
    total_debito = df["DÉBITO"].sum()
    saldo = total_credito - total_debito

    # Exibir dados
    st.subheader("📊 Lançamentos Detalhados")
    
    # Selecionar colunas para exibição
    colunas_exibicao = ["data", "Grupo", "subgrupo", "plano", "descricao", "banco", "entidade", "CRÉDITO", "DÉBITO"]
    colunas_disponiveis = [col for col in colunas_exibicao if col in df.columns]
    
    df_exibir = df[colunas_disponiveis].copy()
    
    # Formatar colunas numéricas
    st.dataframe(
        df_exibir.style.format({
            "CRÉDITO": lambda x: formatar_moeda(x) if x > 0 else "",
            "DÉBITO": lambda x: formatar_moeda(x) if x > 0 else "",
            "data": lambda x: x.strftime("%d/%m/%Y") if isinstance(x, date) else ""
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
        periodo_str = f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
        elements.append(Paragraph(periodo_str, subtitulo_style))

        # Preparar dados da tabela
        colunas = ["Data", "Grupo", "Descrição", "Crédito", "Débito"]
        dados = [colunas]

        for _, row in df.iterrows():
            dados.append([
                row["data"].strftime("%d/%m/%Y") if isinstance(row["data"], date) else "",
                row["Grupo"] or "",
                row["descricao"] or "",
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
        st.success(f"✅ Relatório gerado com sucesso: {caminho_pdf}")
        
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
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # Processar dados
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["CRÉDITO"] = df.apply(lambda x: x["valor"] if x["classificacao"] == "Crédito" else 0, axis=1)
    df["DÉBITO"] = df.apply(lambda x: x["valor"] if x["classificacao"] == "Débito" else 0, axis=1)

    # Agrupar dados
    agrupado = df.groupby(["Grupo", "subgrupo", "plano"], dropna=False).agg({
        "CRÉDITO": "sum",
        "DÉBITO": "sum"
    }).reset_index()

    agrupado = agrupado.sort_values(by=["Grupo", "subgrupo", "plano"])

    # Calcular totais
    total_credito = agrupado["CRÉDITO"].sum()
    total_debito = agrupado["DÉBITO"].sum()
    saldo = total_credito - total_debito

    # Adicionar linha de totais
    linha_total = pd.DataFrame({
        "Grupo": [""],
        "subgrupo": [""],
        "plano": ["TOTAL GERAL"],
        "CRÉDITO": [total_credito],
        "DÉBITO": [total_debito]
    })
    
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
        periodo_str = f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
        elements.append(Paragraph(periodo_str, subtitulo_style))

        # Preparar dados da tabela
        colunas = ["Grupo", "Subgrupo", "Plano", "Crédito", "Débito"]
        dados = [colunas]

        for _, row in agrupado_final.iterrows():
            dados.append([
                row["Grupo"] or "",
                row["subgrupo"] or "",
                row["plano"] or "",
                formatar_moeda(row["CRÉDITO"]),
                formatar_moeda(row["DÉBITO"])
            ])

        # Criar tabela
        tabela = Table(dados, colWidths=[100, 100, 120, 80, 80])
        
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
        st.success(f"✅ Relatório gerado com sucesso: {caminho_pdf}")
        
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
    st.title("📈 Sistema de Relatórios")
    tab1, tab2 = st.tabs(["Relatório Analítico", "Relatório Sintético"])
    
    with tab1:
        rel_analitico()
    
    with tab2:
        rel_sintetico()