# -*- coding: utf-8 -*-
import os
from datetime import datetime, date
import sqlite3
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -------------------------
# CONFIGURAÇÃO / CONSTANTES - ADICIONE ESTA PARTE
# -------------------------
PASTA_RELATORIOS = r"C:\NPS-FIN\Relatorios"
DB_PATH = r"C:\NPS-FIN\modulos\nps_financeiro.db"  # <--- ADICIONE ESTA LINHA
FONT_NAME = "Calibri"
FONT_SIZE_PDF = 10

# Tenta registrar Calibri do Windows, faz fallback se não encontrado
def _registrar_fonte_calibri():
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME
    caminhos_possiveis = [
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\Calibri.ttf",
        r"/usr/share/fonts/truetype/msttcorefonts/Calibri.ttf",
    ]
    for p in caminhos_possiveis:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, p))
                return FONT_NAME
            except Exception:
                continue
    return "Helvetica"

FONT_USADA = _registrar_fonte_calibri()

# -------------------------
# UTILITÁRIOS
# -------------------------
def conectar_db():
    return sqlite3.connect(DB_PATH)

def tabela_existe(conn, tabela):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
    ex = cur.fetchone() is not None
    cur.close()
    return ex

def formatar_moeda(valor):
    try:
        if valor == 0 or pd.isna(valor):
            return ""
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return ""

def formatar_data_brasileira(d):
    try:
        if pd.isna(d):
            return ""
        if isinstance(d, str):
            dts = pd.to_datetime(d, errors="coerce")
            if pd.isna(dts):
                return d
            d = dts.date()
        return d.strftime("%d/%m/%Y")
    except:
        return ""

# -------------------------
# CARREGAMENTO DE DADOS CORRIGIDO
# -------------------------
def carregar_dados_financeiros(data_inicio, data_fim, status_filtro="Todos"):
    conn = conectar_db()
    try:
        if not tabela_existe(conn, "financeiro"):
            st.warning("A tabela 'financeiro' não existe no banco.")
            return pd.DataFrame()

        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(financeiro)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]

        colunas_base = ["data", "valor", "tipo", "grupo", "subgrupo", "plano", "descricao", "relacao", "banco", "status"]
        colunas_selecionar = [c for c in colunas_base if c in colunas_existentes]

        colunas_str = ", ".join(colunas_selecionar)
        query = f"SELECT {colunas_str} FROM financeiro WHERE data BETWEEN ? AND ?"

        def to_iso(d):
            if isinstance(d, date):
                return d.isoformat()
            try:
                return datetime.strptime(d, "%d/%m/%Y").date().isoformat()
            except:
                return d

        params = [to_iso(data_inicio), to_iso(data_fim)]
        if status_filtro != "Todos" and "status" in colunas_existentes:
            query += " AND status = ?"
            params.append(status_filtro)

        query += " ORDER BY data ASC"
        df = pd.read_sql_query(query, conn, params=params)

        if "valor" not in df.columns:
            df["valor"] = 0

        # CORREÇÃO: Cálculo mais robusto de créditos e débitos
        df["CRÉDITO"] = 0.0
        df["DÉBITO"] = 0.0
        
        if "tipo" in df.columns:
            # Para créditos: valores positivos de entradas
            mask_credito = (
                (df["valor"] > 0) & 
                (df["tipo"].astype(str).str.strip().str.lower().isin(["entrada", "credito", "crédito", "receita", "recebimento"]))
            )
            df.loc[mask_credito, "CRÉDITO"] = df.loc[mask_credito, "valor"]
            
            # Para débitos: valores positivos de saídas OU valores negativos convertidos
            mask_debito_valor_negativo = (df["valor"] < 0)
            mask_debito_tipo_saida = (
                (df["valor"] > 0) & 
                (df["tipo"].astype(str).str.strip().str.lower().isin(["saida", "saída", "debito", "débito", "despesa", "pagamento"]))
            )
            df.loc[mask_debito_valor_negativo, "DÉBITO"] = abs(df.loc[mask_debito_valor_negativo, "valor"])
            df.loc[mask_debito_tipo_saida, "DÉBITO"] = df.loc[mask_debito_tipo_saida, "valor"]
        else:
            # Se não há coluna tipo, considerar positivo como crédito e negativo como débito
            df.loc[df["valor"] > 0, "CRÉDITO"] = df.loc[df["valor"] > 0, "valor"]
            df.loc[df["valor"] < 0, "DÉBITO"] = abs(df.loc[df["valor"] < 0, "valor"])

        return df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# -------------------------
# AGRUPAMENTO GENÉRICO CORRIGIDO
# -------------------------
def preparar_agrupamento(df, colunas_agrupamento):
    df_local = df.copy()
    for c in ["CRÉDITO","DÉBITO"]:
        if c not in df_local.columns:
            df_local[c] = 0
    
    colunas_atuais = [c for c in colunas_agrupamento if c in df_local.columns]
    if colunas_atuais:
        df_agr = df_local.groupby(colunas_atuais, dropna=False).agg({
            "CRÉDITO": "sum",
            "DÉBITO": "sum"
        }).reset_index()
        df_agr = df_agr.sort_values(by=colunas_atuais).reset_index(drop=True)
        for c in colunas_atuais:
            df_agr[c] = df_agr[c].astype(str).fillna("").str.strip()
        return df_agr
    else:
        return df_local.sort_values(by=["CRÉDITO","DÉBITO"]).reset_index(drop=True)

# -------------------------
# GERADOR DE PDF PADRÃO COM FONTE 10
# -------------------------
def gerar_pdf_padrao(titulo, subtitulo_filtro, colunas_header, linhas, total_credito, total_debito, saldo, data_inicio, data_fim, nome_arquivo_prefixo):
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{nome_arquivo_prefixo}_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        doc = SimpleDocTemplate(caminho_pdf, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontName=FONT_USADA, fontSize=12, leading=14)
        subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Normal'], alignment=TA_CENTER, fontName=FONT_USADA, fontSize=10)
        resumo_style = ParagraphStyle('Resumo', parent=styles['Normal'], fontName=FONT_USADA, fontSize=10, alignment=TA_RIGHT)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=8, alignment=TA_RIGHT)
        elements = []
        elements.append(Paragraph(titulo, titulo_style))
        periodo_str = f"Período: {formatar_data_brasileira(data_inicio)} a {formatar_data_brasileira(data_fim)}"
        elements.append(Paragraph(periodo_str, subtitulo_style))
        elements.append(Paragraph(f"Filtro aplicado: {subtitulo_filtro}", subtitulo_style))
        elements.append(Spacer(1, 12))
        dados = [colunas_header]
        dados.extend(linhas)
        
        # AJUSTE AUTOMÁTICO DAS COLUNAS
        num_colunas = len(colunas_header)
        largura_total = 750  # Largura disponível na página
        colWidths = [largura_total / num_colunas] * num_colunas
        
        # Ajustes específicos para colunas maiores
        for i, h in enumerate(colunas_header):
            if any(k in h.lower() for k in ["descri", "relac"]):
                colWidths[i] = largura_total * 0.25
            elif "plano" in h.lower() or "subgrupo" in h.lower():
                colWidths[i] = largura_total * 0.15
            elif "grupo" in h.lower():
                colWidths[i] = largura_total * 0.12
            elif "crédito" in h.lower() or "débito" in h.lower():
                colWidths[i] = largura_total * 0.1
            elif "data" in h.lower():
                colWidths[i] = largura_total * 0.08
        
        # Normalizar para não ultrapassar a largura total
        fator_ajuste = largura_total / sum(colWidths)
        colWidths = [w * fator_ajuste for w in colWidths]
        
        tabela = Table(dados, colWidths=colWidths)
        estilo_tabela = TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
            ('FONTSIZE', (0,0), (-1,-1), FONT_SIZE_PDF),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ])
        # Alinhar colunas monetárias à direita
        for i, h in enumerate(colunas_header):
            if "crédito" in h.lower() or "débito" in h.lower():
                estilo_tabela.add('ALIGN', (i,1),(i,-1),'RIGHT')
        tabela.setStyle(estilo_tabela)
        elements.append(tabela)
        elements.append(Spacer(1, 12))
        
        # RESUMO NO FORMATO SOLICITADO
        elements.append(Paragraph(f"Crédito    {formatar_moeda(total_credito)}", resumo_style))
        elements.append(Paragraph(f"Débito     {formatar_moeda(total_debito)}", resumo_style))
        elements.append(Paragraph(f"Saldo      {formatar_moeda(saldo)}", resumo_style))
        
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        with open(caminho_pdf,"rb") as f:
            st.download_button(label="⬇️ Baixar PDF", data=f.read(), file_name=filename, mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")

# -------------------------
# FUNÇÃO PARA ESTILIZAR DATAFRAME COM FONTE CALIBRI 10
# -------------------------
def styled_dataframe(df, height=420):
    """Exibe DataFrame com fonte Calibri tamanho 10 e ajuste automático de colunas"""
    st.markdown("""
        <style>
        .dataframe {
            font-family: Calibri, sans-serif !important;
            font-size: 10pt !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, height=height)

# -------------------------
# RELATÓRIOS CORRIGIDOS
# -------------------------
def rel_analitico():
    st.header("📑 Relatório Analítico")
    col1,col2,col3 = st.columns(3)
    with col1:
        data_inicio_str = st.text_input("Data inicial:", formatar_data_brasileira(date.today()), key="analitico_data_inicio")
    with col2:
        data_fim_str = st.text_input("Data final:", formatar_data_brasileira(date.today()), key="analitico_data_fim")
    with col3:
        status_filtro = st.selectbox("Status", ["Todos","Pago","Aberto"], key="analitico_status_select")
    try:
        data_inicio = datetime.strptime(data_inicio_str, "%d/%m/%Y").date()
        data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y").date()
    except:
        st.warning("⚠️ Formato de data inválido. Use DD/MM/AAAA")
        return
    st.subheader(f"Filtro aplicado: {status_filtro}")
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    df = df.sort_values(by=[c for c in ["data","grupo","plano"] if c in df.columns], ascending=True).reset_index(drop=True)
    total_credito = df["CRÉDITO"].sum()
    total_debito = df["DÉBITO"].sum()
    saldo = total_credito - total_debito
    
    # Garantir que as colunas existam
    for col in ["data","relacao","plano","descricao","grupo"]:
        if col not in df.columns:
            df[col] = ""
    
    # DataFrame para exibição
    df_exibir = pd.DataFrame({
        "Data": df["data"].apply(formatar_data_brasileira),
        "Relação": df["relacao"],
        "Grupo": df["grupo"],
        "Plano": df["plano"],
        "Descrição": df["descricao"],
        "Crédito": df["CRÉDITO"].apply(formatar_moeda),
        "Débito": df["DÉBITO"].apply(formatar_moeda)
    })
    
    # Exibir com estilo Calibri 10
    styled_dataframe(df_exibir, height=420)
    
    # RESUMO NO FORMATO SOLICITADO
    st.markdown("---")
    st.markdown("### Resumo")
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Crédito</b>    {formatar_moeda(total_credito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Débito</b>     {formatar_moeda(total_debito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Saldo</b>      {formatar_moeda(saldo)}</p>', unsafe_allow_html=True)
    
    if st.button("📄 Gerar PDF - Relatório Analítico", key="pdf_analitico"):
        header = list(df_exibir.columns)
        linhas = [[row[h] for h in header] for _, row in df_exibir.iterrows()]
        gerar_pdf_padrao("RELATÓRIO ANALÍTICO", status_filtro, header, linhas, total_credito, total_debito, saldo, data_inicio, data_fim, "relatorio_analitico")

def rel_sintetico():
    st.header("📊 Relatório Sintético")
    col1,col2,col3 = st.columns(3)
    with col1:
        data_inicio_str = st.text_input("Data inicial:", formatar_data_brasileira(date.today()), key="sintetico_data_inicio")
    with col2:
        data_fim_str = st.text_input("Data final:", formatar_data_brasileira(date.today()), key="sintetico_data_fim")
    with col3:
        status_filtro = st.selectbox("Status", ["Todos","Pago","Aberto"], key="sintetico_status_select")
    try:
        data_inicio = datetime.strptime(data_inicio_str,"%d/%m/%Y").date()
        data_fim = datetime.strptime(data_fim_str,"%d/%m/%Y").date()
    except:
        st.warning("⚠️ Formato de data inválido. Use DD/MM/AAAA")
        return
    st.subheader(f"Filtro aplicado: {status_filtro}")
    df = carregar_dados_financeiros(data_inicio,data_fim,status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    colunas_agr = [c for c in ["relacao","grupo","subgrupo","plano"] if c in df.columns]
    df_agrupado = preparar_agrupamento(df,colunas_agr)
    total_credito = df_agrupado["CRÉDITO"].sum()
    total_debito = df_agrupado["DÉBITO"].sum()
    saldo = total_credito - total_debito
    
    # DataFrame para exibição
    df_exibir = pd.DataFrame()
    if "relacao" in df_agrupado.columns:
        df_exibir["Relação"] = df_agrupado["relacao"]
    if "grupo" in df_agrupado.columns:
        df_exibir["Grupo"] = df_agrupado["grupo"]
    if "subgrupo" in df_agrupado.columns:
        df_exibir["Subgrupo"] = df_agrupado["subgrupo"]
    if "plano" in df_agrupado.columns:
        df_exibir["Plano"] = df_agrupado["plano"]
    
    df_exibir["Crédito"] = df_agrupado["CRÉDITO"].apply(formatar_moeda)
    df_exibir["Débito"] = df_agrupado["DÉBITO"].apply(formatar_moeda)
    
    # Exibir com estilo Calibri 10
    styled_dataframe(df_exibir, height=420)
    
    # RESUMO NO FORMATO SOLICITADO
    st.markdown("---")
    st.markdown("### Resumo")
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Crédito</b>    {formatar_moeda(total_credito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Débito</b>     {formatar_moeda(total_debito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Saldo</b>      {formatar_moeda(saldo)}</p>', unsafe_allow_html=True)
    
    if st.button("📄 Gerar PDF - Relatório Sintético", key="pdf_sintetico"):
        header = list(df_exibir.columns)
        linhas = [[row[h] for h in header] for _, row in df_exibir.iterrows()]
        gerar_pdf_padrao("RELATÓRIO SINTÉTICO", status_filtro, header, linhas, total_credito, total_debito, saldo, data_inicio, data_fim, "relatorio_sintetico")

def relacao_analitico():
    st.header("📑 Relação Analítico")
    col1,col2,col3 = st.columns(3)
    with col1:
        data_inicio_str = st.text_input("Data inicial:", formatar_data_brasileira(date.today()), key="relacao_analitico_data_inicio")
    with col2:
        data_fim_str = st.text_input("Data final:", formatar_data_brasileira(date.today()), key="relacao_analitico_data_fim")
    with col3:
        status_filtro = st.selectbox("Status", ["Todos","Pago","Aberto"], key="relacao_analitico_status")
    try:
        data_inicio = datetime.strptime(data_inicio_str,"%d/%m/%Y").date()
        data_fim = datetime.strptime(data_fim_str,"%d/%m/%Y").date()
    except:
        st.warning("⚠️ Formato de data inválido. Use DD/MM/AAAA")
        return
    st.subheader(f"Filtro aplicado: {status_filtro}")
    df = carregar_dados_financeiros(data_inicio,data_fim,status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    df = df.sort_values(by=[c for c in ["relacao","descricao","data"] if c in df.columns], ascending=True).reset_index(drop=True)
    total_credito = df["CRÉDITO"].sum()
    total_debito = df["DÉBITO"].sum()
    saldo = total_credito - total_debito
    
    # DataFrame para exibição
    df_exibir = pd.DataFrame({
        "Data": df["data"].apply(formatar_data_brasileira),
        "Relação": df["relacao"],
        "Plano": df["plano"] if "plano" in df.columns else "",
        "Descrição": df["descricao"] if "descricao" in df.columns else "",
        "Crédito": df["CRÉDITO"].apply(formatar_moeda),
        "Débito": df["DÉBITO"].apply(formatar_moeda)
    })
    
    # Exibir com estilo Calibri 10
    styled_dataframe(df_exibir, height=420)
    
    # RESUMO NO FORMATO SOLICITADO
    st.markdown("---")
    st.markdown("### Resumo")
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Crédito</b>    {formatar_moeda(total_credito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Débito</b>     {formatar_moeda(total_debito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Saldo</b>      {formatar_moeda(saldo)}</p>', unsafe_allow_html=True)
    
    if st.button("📄 Gerar PDF - Relação Analítico", key="pdf_relacao_analitico"):
        header = list(df_exibir.columns)
        linhas = [[row[h] for h in header] for _, row in df_exibir.iterrows()]
        gerar_pdf_padrao("RELATÓRIO RELAÇÃO ANALÍTICO", status_filtro, header, linhas, total_credito, total_debito, saldo, data_inicio, data_fim, "relacao_analitico")

def relacao_sintetico():
    st.header("📊 Relação Sintético")
    col1,col2,col3 = st.columns(3)
    with col1:
        data_inicio_str = st.text_input("Data inicial:", formatar_data_brasileira(date.today()), key="relacao_sintetico_data_inicio")
    with col2:
        data_fim_str = st.text_input("Data final:", formatar_data_brasileira(date.today()), key="relacao_sintetico_data_fim")
    with col3:
        status_filtro = st.selectbox("Status", ["Todos","Pago","Aberto"], key="relacao_sintetico_status")
    try:
        data_inicio = datetime.strptime(data_inicio_str,"%d/%m/%Y").date()
        data_fim = datetime.strptime(data_fim_str,"%d/%m/%Y").date()
    except:
        st.warning("⚠️ Formato de data inválido. Use DD/MM/AAAA")
        return
    st.subheader(f"Filtro aplicado: {status_filtro}")
    df = carregar_dados_financeiros(data_inicio,data_fim,status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    colunas_agr = [c for c in ["grupo","relacao","subgrupo"] if c in df.columns]
    df_agrupado = preparar_agrupamento(df,colunas_agr)
    total_credito = df_agrupado["CRÉDITO"].sum()
    total_debito = df_agrupado["DÉBITO"].sum()
    saldo = total_credito - total_debito
    
    # DataFrame para exibição
    df_exibir = pd.DataFrame()
    if "grupo" in df_agrupado.columns:
        df_exibir["Grupo"] = df_agrupado["grupo"]
    if "relacao" in df_agrupado.columns:
        df_exibir["Relação"] = df_agrupado["relacao"]
    if "subgrupo" in df_agrupado.columns:
        df_exibir["Subgrupo"] = df_agrupado["subgrupo"]
    
    df_exibir["Crédito"] = df_agrupado["CRÉDITO"].apply(formatar_moeda)
    df_exibir["Débito"] = df_agrupado["DÉBITO"].apply(formatar_moeda)
    
    # Exibir com estilo Calibri 10
    styled_dataframe(df_exibir, height=420)
    
    # RESUMO NO FORMATO SOLICITADO
    st.markdown("---")
    st.markdown("### Resumo")
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Crédito</b>    {formatar_moeda(total_credito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Débito</b>     {formatar_moeda(total_debito)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Calibri; font-size:10pt; margin: 2px 0;"><b>Saldo</b>      {formatar_moeda(saldo)}</p>', unsafe_allow_html=True)
    
    if st.button("📄 Gerar PDF - Relação Sintético", key="pdf_relacao_sintetico"):
        header = list(df_exibir.columns)
        linhas = [[row[h] for h in header] for _, row in df_exibir.iterrows()]
        gerar_pdf_padrao("RELATÓRIO RELAÇÃO SINTÉTICO", status_filtro, header, linhas, total_credito, total_debito, saldo, data_inicio, data_fim, "relacao_sintetico")

def mov_caixa_banco():
    try:
        st.header("🏦 Movimento Diário - Caixa/Banco")
        
        col1, col2 = st.columns(2)
        with col1:
            data_relatorio_str = st.text_input("Data do relatório:", formatar_data_brasileira(date.today()), key="mov_caixa_data")
        with col2:
            status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="mov_caixa_status")
        
        try:
            data_relatorio = datetime.strptime(data_relatorio_str, "%d/%m/%Y").date()
        except:
            st.warning("⚠️ Formato de data inválido. Use DD/MM/AAAA")
            return
        
        # Carregar dados do dia específico
        df = carregar_dados_financeiros(data_relatorio, data_relatorio, status_filtro)
        
        if df.empty:
            st.warning("Nenhum movimento encontrado para esta data.")
            return
        
        # Garantir que a coluna banco existe
        if "banco" not in df.columns:
            df["banco"] = "Carteira"
        df["banco"] = df["banco"].fillna("Carteira")
        
        bancos = sorted(df["banco"].unique())
        
        # Variáveis para cálculo do saldo total
        saldo_total_contas = 0
        
        # Para cada banco
        for banco in bancos:
            st.markdown("---")
            
            # Cabeçalho do banco
            st.markdown(f"**Movimento do dia {formatar_data_brasileira(data_relatorio)}**")
            st.markdown(f"**Banco:** {banco}")
            
            # Filtrar dados do banco atual
            df_banco = df[df["banco"] == banco].copy()
            
            # CALCULAR SALDO ANTERIOR (até o dia anterior) - apenas transações pagas
            data_anterior = data_relatorio - pd.Timedelta(days=1)
            df_historico = carregar_dados_financeiros(date(1900, 1, 1), data_anterior, "Pago")
            
            saldo_anterior = 0
            if not df_historico.empty and "banco" in df_historico.columns:
                df_historico_banco = df_historico[df_historico["banco"] == banco]
                saldo_anterior = df_historico_banco["CRÉDITO"].sum() - df_historico_banco["DÉBITO"].sum()
            
            # Calcular movimento do dia
            credito_dia = df_banco["CRÉDITO"].sum()
            debito_dia = df_banco["DÉBITO"].sum()
            movimento_dia = credito_dia - debito_dia
            
            # CALCULAR SALDO ATUAL
            saldo_atual = saldo_anterior + movimento_dia
            saldo_total_contas += saldo_atual
            
            # Exibir saldo anterior
            st.markdown(f"**Saldo anterior................................................................................................................:** {formatar_moeda(saldo_anterior)}")
            st.markdown("")
            
            # Preparar dados para exibição da tabela
            dados_tabela = []
            for _, row in df_banco.iterrows():
                dados_tabela.append({
                    "Data": formatar_data_brasileira(row["data"]),
                    "Plano": str(row["plano"]) if "plano" in row and pd.notna(row["plano"]) else "",
                    "Descrição": str(row["descricao"]) if "descricao" in row and pd.notna(row["descricao"]) else "",
                    "Entrada": formatar_moeda(row["CRÉDITO"]),
                    "Saída": formatar_moeda(row["DÉBITO"])
                })
            
            # Exibir tabela
            if dados_tabela:
                df_exibir = pd.DataFrame(dados_tabela)
                
                # Estilizar a tabela para ficar mais clean
                st.markdown("""
                <style>
                .dataframe {
                    font-family: Calibri, sans-serif;
                    font-size: 10pt;
                }
                .dataframe thead th {
                    background-color: #f0f0f0;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma transação para este banco")
            
            # Espaço
            st.markdown("")
            
            # Exibir saldo atual
            st.markdown(f"**Saldo atual {banco}.......................................................................................................:** {formatar_moeda(saldo_atual)}")
            st.markdown("")
        
        # Exibir saldo total de todas as contas (quando houver mais de um banco)
        if len(bancos) > 1:
            st.markdown("---")
            st.markdown(f"**Saldo total das contas.....................................................................................................:** {formatar_moeda(saldo_total_contas)}")
        
        # Botão para gerar PDF
        if st.button("📄 Gerar PDF - Movimento Diário", key="pdf_mov_caixa"):
            gerar_pdf_movimento_caixa(data_relatorio, status_filtro, df, bancos)
            
    except Exception as e:
        st.error(f"Erro ao exibir movimento do caixa: {e}")

def gerar_pdf_movimento_caixa(data_relatorio, status_filtro, df, bancos):
    """Gera PDF no layout solicitado"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimento_caixa_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=14, leading=16, spaceAfter=12)
        banco_style = ParagraphStyle('Banco', parent=styles['Heading2'], alignment=TA_LEFT,
                                   fontName=FONT_USADA, fontSize=12, leading=14, spaceAfter=6)
        saldo_style = ParagraphStyle('Saldo', parent=styles['Normal'], alignment=TA_LEFT,
                                   fontName=FONT_USADA, fontSize=10, leading=12, spaceAfter=6)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=8, alignment=TA_RIGHT)
        
        elements = []
        
        # Título principal
        elements.append(Paragraph(f"Movimento do dia {formatar_data_brasileira(data_relatorio)}", titulo_style))
        elements.append(Paragraph(f"Filtro aplicado: {status_filtro}", titulo_style))
        elements.append(Spacer(1, 12))
        
        saldo_total_contas = 0
        
        # Para cada banco
        for banco in bancos:
            # Filtrar dados do banco
            df_banco = df[df["banco"] == banco].copy()
            
            # Calcular saldo anterior
            data_anterior = data_relatorio - pd.Timedelta(days=1)
            df_historico = carregar_dados_financeiros(date(1900, 1, 1), data_anterior, "Pago")
            
            saldo_anterior = 0
            if not df_historico.empty and "banco" in df_historico.columns:
                df_historico_banco = df_historico[df_historico["banco"] == banco]
                saldo_anterior = df_historico_banco["CRÉDITO"].sum() - df_historico_banco["DÉBITO"].sum()
            
            # Calcular totais do dia
            credito_dia = df_banco["CRÉDITO"].sum()
            debito_dia = df_banco["DÉBITO"].sum()
            saldo_atual = saldo_anterior + credito_dia - debito_dia
            saldo_total_contas += saldo_atual
            
            # Cabeçalho do banco
            elements.append(Paragraph(f"Banco: {banco}", banco_style))
            elements.append(Paragraph(f"Saldo anterior................................................................................................................: {formatar_moeda(saldo_anterior)}", saldo_style))
            elements.append(Spacer(1, 6))
            
            # Cabeçalho da tabela
            dados_tabela = [["Data", "Plano", "Descrição", "Entrada", "Saída"]]
            
            # Dados das transações
            for _, row in df_banco.iterrows():
                data_str = formatar_data_brasileira(row["data"])
                plano = str(row["plano"]) if "plano" in row and pd.notna(row["plano"]) else ""
                descricao = str(row["descricao"]) if "descricao" in row and pd.notna(row["descricao"]) else ""
                entrada = formatar_moeda(row["CRÉDITO"])
                saida = formatar_moeda(row["DÉBITO"])
                
                dados_tabela.append([data_str, plano, descricao, entrada, saida])
            
            # Criar tabela
            if len(dados_tabela) > 1:
                tabela = Table(dados_tabela, colWidths=[80, 100, 200, 80, 80])
                estilo_tabela = TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
                    ('FONTSIZE', (0,0), (-1,-1), FONT_SIZE_PDF),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('ALIGN', (3,1), (4,-1), 'RIGHT'),
                ])
                tabela.setStyle(estilo_tabela)
                elements.append(tabela)
            else:
                elements.append(Paragraph("Nenhuma transação neste banco.", saldo_style))
            
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"Saldo atual {banco}.......................................................................................................: {formatar_moeda(saldo_atual)}", saldo_style))
            elements.append(Spacer(1, 12))
        
        # Saldo total das contas (quando houver mais de um banco)
        if len(bancos) > 1:
            elements.append(Paragraph(f"Saldo total das contas.....................................................................................................: {formatar_moeda(saldo_total_contas)}", saldo_style))
            elements.append(Spacer(1, 12))
        
        # Rodapé
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        
        # Construir PDF
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        
        # Botão de download
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar PDF - Movimento Diário", 
                data=f.read(), 
                file_name=filename, 
                mime="application/pdf", 
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")

def gerar_pdf_movimento_caixa(data_relatorio, status_filtro, df, bancos):
    """Gera PDF específico para movimento diário de caixa/banco"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimento_caixa_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=14, leading=16, spaceAfter=12)
        banco_style = ParagraphStyle('Banco', parent=styles['Heading2'], alignment=TA_LEFT,
                                   fontName=FONT_USADA, fontSize=12, leading=14, spaceAfter=6)
        saldo_style = ParagraphStyle('Saldo', parent=styles['Normal'], alignment=TA_LEFT,
                                   fontName=FONT_USADA, fontSize=10, leading=12, spaceAfter=6)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=8, alignment=TA_RIGHT)
        
        elements = []
        
        # Título principal
        elements.append(Paragraph(f"Movimento do dia {formatar_data_brasileira(data_relatorio)}", titulo_style))
        elements.append(Paragraph(f"Filtro aplicado: {status_filtro}", titulo_style))
        elements.append(Spacer(1, 12))
        
        # Para cada banco
        for banco in bancos:
            # Filtrar dados do banco
            df_banco = df[df["banco"] == banco].copy()
            
            # Calcular saldo anterior COM MESMO FILTRO
            data_anterior = data_relatorio - pd.Timedelta(days=1)
            df_historico = carregar_dados_financeiros(date(1900, 1, 1), data_anterior, status_filtro)
            
            saldo_anterior = 0
            if not df_historico.empty and "banco" in df_historico.columns:
                df_historico_banco = df_historico[df_historico["banco"] == banco]
                saldo_anterior = df_historico_banco["CRÉDITO"].sum() - df_historico_banco["DÉBITO"].sum()
            
            # Calcular totais do dia
            credito_dia = df_banco["CRÉDITO"].sum()
            debito_dia = df_banco["DÉBITO"].sum()
            saldo_atual = saldo_anterior + credito_dia - debito_dia
            
            # Cabeçalho do banco
            elements.append(Paragraph(f"Banco: {banco}", banco_style))
            elements.append(Paragraph(f"Saldo anterior.......................................................................................................................... : {formatar_moeda(saldo_anterior)}", saldo_style))
            elements.append(Spacer(1, 6))
            
            # Cabeçalho da tabela
            dados_tabela = [["Data", "Plano", "Descrição", "Entrada", "Saída"]]
            
            # Dados das transações
            for _, row in df_banco.iterrows():
                data_str = formatar_data_brasileira(row["data"])
                plano = str(row["plano"]) if "plano" in row and pd.notna(row["plano"]) else ""
                descricao = str(row["descricao"]) if "descricao" in row and pd.notna(row["descricao"]) else ""
                entrada = formatar_moeda(row["CRÉDITO"])
                saida = formatar_moeda(row["DÉBITO"])
                
                dados_tabela.append([data_str, plano, descricao, entrada, saida])
            
            # Criar tabela
            if len(dados_tabela) > 1:  # Se há transações além do cabeçalho
                tabela = Table(dados_tabela, colWidths=[80, 100, 200, 80, 80])
                estilo_tabela = TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
                    ('FONTSIZE', (0,0), (-1,-1), FONT_SIZE_PDF),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('ALIGN', (3,1), (4,-1), 'RIGHT'),  # Alinhar colunas monetárias à direita
                ])
                tabela.setStyle(estilo_tabela)
                elements.append(tabela)
            else:
                elements.append(Paragraph("Nenhuma transação neste banco.", saldo_style))
            
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"Saldo do Banco: {banco}........................................................................................................: {formatar_moeda(saldo_atual)}", saldo_style))
            elements.append(Spacer(1, 12))
            
            # Linha separadora
            elements.append(Paragraph("_____________________________________________________________________________________________________", saldo_style))
            elements.append(Spacer(1, 12))
        
        # Rodapé
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        
        # Construir PDF
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        
        # Botão de download
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar PDF - Movimento Diário", 
                data=f.read(), 
                file_name=filename, 
                mime="application/pdf", 
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
# -------------------------
# MAIN
# -------------------------
# No final do arquivo, modifique o main para:
if __name__ == "__main__":
    st.title("📈 Sistema de Relatórios Financeiros")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Relatório Analítico", 
        "Relatório Sintético", 
        "Relação Analítico", 
        "Relação Sintético",
        "Movimento Diário"
    ])
    with tab1: rel_analitico()
    with tab2: rel_sintetico()
    with tab3: relacao_analitico()
    with tab4: relacao_sintetico()
    with tab5: mov_caixa_banco()