# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import tempfile
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fpdf import FPDF
from datetime import datetime, date
# -------------------------
# CONFIGURAÇÃO / CONSTANTES - CORRIGIDA
# -------------------------

def get_base_path():
    """Retorna o caminho base CORRETO para desenvolvimento e produção"""
    if getattr(sys, 'frozen', False):
        # Executável PyInstaller - usa pasta do executável
        return os.path.dirname(sys.executable)
    else:
        # DESENVOLVIMENTO - usa caminho específico do projeto
        return r"C:\NPS-FIN\dist"

BASE_PATH = get_base_path()

# Caminhos relativos
DB_PATH = os.path.join(BASE_PATH, "nps_financeiro.db")
PASTA_RELATORIOS = os.path.join(BASE_PATH, "Relatorios")

# Criar pasta de relatórios se não existir
os.makedirs(PASTA_RELATORIOS, exist_ok=True)

FONT_NAME = "Calibri"
FONT_SIZE_PDF = 9

def verificar_banco_dados():
    """Verifica se o banco de dados existe e está acessível"""
    st.sidebar.info(f"**Modo:** {'EXECUTÁVEL' if getattr(sys, 'frozen', False) else 'DESENVOLVIMENTO'}")
    st.sidebar.info(f"**Base Path:** {BASE_PATH}")
    st.sidebar.info(f"**DB Path:** {DB_PATH}")
    
    if os.path.exists(DB_PATH):
        st.sidebar.success("✅ Banco de dados ENCONTRADO")
        try:
            # Testar conexão
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = cursor.fetchall()
            conn.close()
            st.sidebar.success(f"✅ Conexão OK - {len(tabelas)} tabelas")
            return True
        except Exception as e:
            st.sidebar.error(f"❌ Erro na conexão: {e}")
            return False
    else:
        st.sidebar.error("❌ Banco de dados NÃO encontrado")
        st.sidebar.info("📁 Arquivos na pasta:")
        try:
            arquivos = os.listdir(BASE_PATH)
            for arq in arquivos[:10]:  # Mostra os primeiros 10 arquivos
                st.sidebar.text(f"  {arq}")
        except:
            st.sidebar.text("  Não foi possível listar arquivos")
        return False

def styled_subheader(text, font_size="16px", color="#171ae0"):
    """Exibe um subtítulo com fonte personalizada"""
    st.markdown(
        f"""
        <div style="
            font-size: {font_size};
            font-weight: bold;
            color: {color};
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin-bottom: 10px;
            margin-top: 20px;
            padding: 5px 0;
            border-bottom: 1px solid #ddd;
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )

def _registrar_fonte_calibri():
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME
    
    caminhos_possiveis = [
        os.path.join(BASE_PATH, "fonts", "calibri.ttf"),
        os.path.join(BASE_PATH, "calibri.ttf"),
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\Calibri.ttf",
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
    """Conecta ao banco de dados com tratamento de erro"""
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o banco de dados: {e}")
        return None

def tabela_existe(conn, tabela):
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
        ex = cur.fetchone() is not None
        cur.close()
        return ex
    except:
        return False

def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    try:
        if pd.isna(valor) or valor == 0:
            return ""
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return ""

def date_input_br(d):
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
# CARREGAMENTO DE DADOS
# -------------------------
def carregar_dados_financeiros(data_inicio, data_fim, status_filtro="Todos"):
    conn = conectar_db()
    if conn is None:
        return pd.DataFrame()
        
    try:
        if not tabela_existe(conn, "financeiro"):
            st.warning("A tabela 'financeiro' não existe no banco.")
            return pd.DataFrame()

        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(financeiro)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]

        colunas_base = ["data", "valor", "tipo", "grupo", "subgrupo", "categoria","plano", "descricao", "relacao", "banco", "status"]
        colunas_selecionar = [c for c in colunas_base if c in colunas_existentes]

        if not colunas_selecionar:
            st.warning("Nenhuma coluna encontrada na tabela financeiro.")
            return pd.DataFrame()

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

        if df.empty:
            return df

        if "valor" not in df.columns:
            df["valor"] = 0

        df["CRÉDITO"] = 0.0
        df["DÉBITO"] = 0.0
        
        if "tipo" in df.columns:
            df["tipo_clean"] = df["tipo"].astype(str).str.strip().str.lower()
            
            mask_credito = (
                (df["valor"] > 0) & 
                (df["tipo_clean"].isin(["entrada", "credito", "crédito", "receita", "recebimento"]))
            )
            df.loc[mask_credito, "CRÉDITO"] = df.loc[mask_credito, "valor"]
            
            mask_debito = (
                (df["valor"] > 0) & 
                (df["tipo_clean"].isin(["saida", "saída", "debito", "débito", "despesa", "pagamento"]))
            )
            df.loc[mask_debito, "DÉBITO"] = df.loc[mask_debito, "valor"]
            
            mask_credito_negativo = (
                (df["valor"] < 0) & 
                (df["tipo_clean"].isin(["saida", "saída", "debito", "débito", "despesa", "pagamento"]))
            )
            mask_debito_negativo = (
                (df["valor"] < 0) & 
                (df["tipo_clean"].isin(["entrada", "credito", "crédito", "receita", "recebimento"]))
            )
            
            df.loc[mask_credito_negativo, "CRÉDITO"] = abs(df.loc[mask_credito_negativo, "valor"])
            df.loc[mask_debito_negativo, "DÉBITO"] = abs(df.loc[mask_debito_negativo, "valor"])
            
            df.drop("tipo_clean", axis=1, inplace=True)
        else:
            df.loc[df["valor"] > 0, "CRÉDITO"] = df.loc[df["valor"] > 0, "valor"]
            df.loc[df["valor"] < 0, "DÉBITO"] = abs(df.loc[df["valor"] < 0, "valor"])

        return df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# -------------------------
# AGRUPAMENTO GENÉRICO
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
# ESTILO UNIFICADO
# -------------------------
def aplicar_estilo_unificado():
    """Aplica estilo unificado para todos os relatórios"""
    st.markdown("""
    <style>
    /* ESTILO UNIFICADO PARA TODOS OS RELATÓRIOS */
    .relatorio-container {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        font-family: Calibri, sans-serif !important;
    }
    
    /* Input fields com estilo escuro */
    .stTextInput input, .stSelectbox select {
        background-color: #2E2E2E !important;
        color: #FFFFFF !important;
        border: 1px solid #555555 !important;
    }
    
    .relatorio-tabela {
        width: 90%;
        font-family: Calibri, sans-serif;
        font-size: 10pt;
        border-collapse: collapse;
        background-color: #000000;
        color: #FFFFFF;
        margin: 10px 0;
    }
    .relatorio-tabela th {
        background-color: #1E3A5F !important;
        color: #FFFFFF !important;
        text-align: left;
        padding: 10px 12px;
        font-weight: bold;
        border: 1px solid #555555;
        font-size: 11pt;
    }
    .relatorio-tabela td {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        padding: 8px 12px;
        border: 1px solid #444444;
        font-size: 10pt;
    }
    .money-col {
        text-align: right;
        font-family: 'Courier New', monospace;
        padding-right: 15px;
    }
    
    .header-relatorio {
        background-color: #000000;
        color: #FFFFFF;
        font-family: Calibri, sans-serif;
        font-size: 11pt;
        margin: 8px 0;
        padding: 5px 0;
    }
    
    .resumo-container {
        background-color: #1A1A1A;
        color: #FFFFFF;
        font-family: Calibri, sans-serif;
        font-size: 11pt;
        margin: 15px 0;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #444444;
    }
    
    .linha-resumo {
        display: flex;
        justify-content: space-between;
        margin: 3px 0;
        font-family: 'Courier New', monospace;
    }
    .label-resumo {
        flex: 1;
        text-align: left;
    }
    .valor-resumo {
        flex: 0 0 150px;
        text-align: right;
        font-family: 'Courier New', monospace;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# FUNÇÕES DE ORDENAÇÃO
# -------------------------
def ordenar_transacoes(df):
    """Ordena transações: Entradas primeiro (ordem alfabética), depois Saídas (ordem alfabética)"""
    df_ordenado = df.copy()
    
    # Criar coluna auxiliar para ordenação
    df_ordenado['tipo_ordem'] = df_ordenado.apply(
        lambda x: 1 if x['CRÉDITO'] > 0 else 2,  # 1 = Entrada, 2 = Saída
        axis=1
    )
    
    # Ordenar: tipo (entradas primeiro), plano (alfabético)
    df_ordenado = df_ordenado.sort_values(
        by=['tipo_ordem', 'plano'], 
        ascending=[True, True]
    ).reset_index(drop=True)
    
    # Remover coluna auxiliar
    df_ordenado = df_ordenado.drop('tipo_ordem', axis=1)
    
    return df_ordenado

def ordenar_por_relacao(df):
    """Ordena por relacao: Primeiro quem tem CRÉDITO, depois alfabético"""
    df_ordenado = df.copy()
    
    if 'relacao' not in df_ordenado.columns:
        return df_ordenado
    
    # CORREÇÃO: Ordenar por CRÉDITO primeiro (receitas no topo), depois alfabético
    df_ordenado['tem_credito'] = df_ordenado['CRÉDITO'] > 0
    
    df_ordenado = df_ordenado.sort_values(
        by=['tem_credito', 'relacao'], 
        ascending=[False, True]  # False = True primeiro (receitas no topo)
    ).reset_index(drop=True)
    
    # Remover coluna auxiliar
    df_ordenado = df_ordenado.drop('tem_credito', axis=1)
    
    return df_ordenado

# -------------------------
# FUNÇÕES DE EXIBIÇÃO
# -------------------------
def display_tabela_unificada(df, tipo_relatorio="movimento"):
    """Exibe tabela com estilo unificado para todos os relatórios"""
    
    # CORREÇÃO: AGRUPAR POR "subgrupo" PARA REL_SINTETICO
    if tipo_relatorio == "sintetico":
        # Agrupamento por relacao (relacao_sintetico)
        df_filtrado_transf = df[df['subgrupo'] != 'Transferências'].copy()
        df_agrupado = df_filtrado_transf.groupby('relacao', as_index=False).agg({
            'CRÉDITO': 'sum', 'DÉBITO': 'sum', 'grupo': 'first', 'subgrupo': 'first', 'plano': 'first'
        })
        
    elif tipo_relatorio == "rel_sintetico":
        # CORREÇÃO: Agrupamento por subgrupo (rel_sintetico)
        df_filtrado_transf = df[df['plano'] != 'Transferências'].copy()
        df_agrupado = df_filtrado_transf.groupby('subgrupo', as_index=False).agg({
            'CRÉDITO': 'sum', 'DÉBITO': 'sum', 'plano': 'first','subgrupo': 'first' # fiz alteração aqui, remover ou não
        })
        
    else:
        # Para outros relatórios, manter lógica original
        df_agrupado = df
    
    # Aplicar filtro de valores zerados NO DADO AGRUPADO
    df_filtrado = df_agrupado[(df_agrupado["CRÉDITO"] != 0) | (df_agrupado["DÉBITO"] != 0)].copy()
    
    if df_filtrado.empty:
        st.info("Nenhuma transação com valores não zerados encontrada")
        return df_filtrado
    
    # Ordenar transações conforme critério
    if tipo_relatorio == "movimento":
        df_ordenado = ordenar_transacoes(df_filtrado)
        
    elif tipo_relatorio == "sintetico":
        df_ordenado = ordenar_por_relacao(df_filtrado)  # Ordena por relacao
        
    elif tipo_relatorio == "rel_sintetico":
        # CORREÇÃO: Ordenar PRIMEIRO por Crédito, DEPOIS por Débito
        df_ordenado = df_filtrado.sort_values(
            by=['CRÉDITO', 'DÉBITO'], 
            ascending=[False, False]
        )

    else:
        df_ordenado = df_filtrado.sort_values(by=['data', 'descricao']).reset_index(drop=True)
    
    # Definir colunas conforme o tipo de relatório
    if tipo_relatorio == "analitico":
        colunas = ["Data", "relacao", "Plano", "Descrição", "Crédito", "Débito"]
        col_widths = [80, 140, 120, 180, 100, 100]
    elif tipo_relatorio == "sintetico":
        colunas = ["relacao", "Plano", "Crédito", "Débito"]
        col_widths = [150,150, 100, 100]
    elif tipo_relatorio == "rel_sintetico":
        # CORREÇÃO: Colunas específicas para rel_sintetico
        colunas = ["Subgrupo", "Crédito", "Débito"]
        col_widths = [150, 100, 100]
    elif tipo_relatorio == "movimento":
        colunas = ["Data", "Plano", "Descrição", "Entrada", "Saída"]
        col_widths = [80, 120, 250, 100, 100]
    else:
        colunas = list(df_ordenado.columns)
        col_widths = [150] * len(colunas)
    
    # Preparar dados
    dados_tabela = []
    for _, row in df_ordenado.iterrows():
        if tipo_relatorio == "movimento":
            entrada = formatar_moeda(row["CRÉDITO"]) if row["CRÉDITO"] > 0 else ""
            saida = formatar_moeda(row["DÉBITO"]) if row["DÉBITO"] > 0 else ""
            
            dados_tabela.append({
                "Data": date_input_br(row["data"]),
                "Plano": str(row["plano"]) if pd.notna(row["plano"]) else "",
                "Descrição": str(row["descricao"]) if pd.notna(row["descricao"]) else "",
                "Entrada": entrada,
                "Saída": saida
            })
        elif tipo_relatorio == "analitico":
            dados_tabela.append({
                "Data": date_input_br(row["data"]),
                "relacao": str(row["relacao"]) if pd.notna(row["relacao"]) else "",
                #"Subgrupo": str(row["grupo"]) if pd.notna(row["grupo"]) else "",
                "Plano": str(row["plano"]) if pd.notna(row["plano"]) else "",
                "Descrição": str(row["descricao"]) if pd.notna(row["descricao"]) else "",
                "Crédito": formatar_moeda(row["CRÉDITO"]),
                "Débito": formatar_moeda(row["DÉBITO"])
            })
        elif tipo_relatorio == "sintetico":
            dados_tabela.append({
                "relacao": str(row["relacao"]) if pd.notna(row["relacao"]) else "",
                #"Subgrupo": str(row["subgrupo"]) if pd.notna(row["subgrupo"]) else "",
                "Plano": str(row["plano"]) if pd.notna(row["plano"]) else "",
                "Crédito": formatar_moeda(row["CRÉDITO"]),
                "Débito": formatar_moeda(row["DÉBITO"])
            })
        elif tipo_relatorio == "rel_sintetico":
            # CORREÇÃO: Dados específicos para rel_sintetico
            dados_tabela.append({
                "Subgrupo": str(row["subgrupo"]) if pd.notna(row["subgrupo"]) else "",
                #"Plano": str(row["plano"]) if pd.notna(row["plano"]) else "",
                "Crédito": formatar_moeda(row["CRÉDITO"]),
                "Débito": formatar_moeda(row["DÉBITO"])
            })

    if not dados_tabela:
        st.info("Nenhuma transação encontrada")
        return df_ordenado
    
    # Criar HTML da tabela
    html = f"""
    <table class="relatorio-tabela">
        <thead>
            <tr>
                {' '.join([f'<th>{col}</th>' for col in colunas])}
            </tr>
        </thead>
        <tbody>
    """
    
    for linha in dados_tabela:
        html += "<tr>"
        for col in colunas:
            if col in ["Crédito", "Débito", "Entrada", "Saída"]:
                html += f'<td class="money-col">{linha[col]}</td>'
            else:
                html += f'<td>{linha[col]}</td>'
        html += "</tr>"
    
    html += "</tbody></table>"
    
    st.markdown(html, unsafe_allow_html=True)
    
    return df_ordenado

def display_resumo_movimento(saldo_anterior, credito_dia, debito_dia, saldo_atual):
    """Exibe resumo formatado para movimento de caixa"""
    
    html = """
    <div class="resumo-container">
        <div class="linha-resumo">
            <span class="label-resumo">Saldo anterior......................................</span>
            <span class="valor-resumo">:</span>
            <span class="valor-resumo">""" + formatar_moeda(saldo_anterior) + """</span>
        </div>
        <div class="linha-resumo">
            <span class="label-resumo">Total das entrada................................</span>
            <span class="valor-resumo">:</span>
            <span class="valor-resumo">""" + formatar_moeda(credito_dia) + """</span>
        </div>
        <div class="linha-resumo">
            <span class="label-resumo">Total das saídas ................................</span>
            <span class="valor-resumo">:</span>
            <span class="valor-resumo">""" + formatar_moeda(debito_dia) + """</span>
        </div>
        <div class="linha-resumo">
            <span class="label-resumo">Saldo Atual..........................................</span>
            <span class="valor-resumo">:</span>
            <span class="valor-resumo">""" + formatar_moeda(saldo_atual) + """</span>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)

# -------------------------
# FUNÇÕES PDF PARA TODOS OS RELATÓRIOS
# -------------------------
def calcular_larguras_colunas_automaticas(colunas, tipo_relatorio):
    """Calcula larguras de colunas automaticamente para caber em A4"""
    if tipo_relatorio == "analitico":
        # Para A4 paisagem - largura total ~780
        return [60, 80, 80, 90, 250, 80, 80]  # Total: 720
    elif tipo_relatorio == "sintetico":
        # Para A4 paisagem - largura total ~780  
        return [150, 120, 120, 150, 100, 100]  # Total: 740
    elif tipo_relatorio == "movimento":
        # Para A4 retrato - largura total ~530
        return [60, 100, 200, 80, 80]  # Total: 520
    elif tipo_relatorio == "rel_sintetico":
        # Para A4 paisagem - largura total ~780
        return [200, 120, 120, 120, 100, 100]  # Total: 760
    else:
        # Distribuição proporcional genérica
        num_cols = len(colunas)
        largura_total = 530 if tipo_relatorio in ["movimento"] else 750
        return [largura_total // num_cols] * num_cols

def gerar_pdf_movimento_caixa(data_relatorio, status_filtro, df, bancos):
    """Gera PDF para movimento diário de caixa/banco"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimento_caixa_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=12, leading=14, spaceAfter=12)
        banco_style = ParagraphStyle('Banco', parent=styles['Heading2'], alignment=TA_LEFT,
                                   fontName=FONT_USADA, fontSize=9
                                   , leading=12, spaceAfter=6)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], alignment=TA_LEFT,
                                    fontName=FONT_USADA, fontSize=9, leading=11)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=7, alignment=TA_RIGHT)
        
        elements = []
        
        # Título principal
        elements.append(Paragraph(f"MOVIMENTO DIÁRIO", titulo_style))
        elements.append(Paragraph(f"Data: {date_input_br(date.today())}", normal_style))
        elements.append(Paragraph(f"Data do Movimento: {date_input_br(data_relatorio)}", normal_style))
        elements.append(Paragraph(f"Filtro: {status_filtro}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Para cada banco
        for banco in bancos:
            # Filtrar dados do banco
            df_banco = df[df["banco"] == banco].copy()
            
            # Filtrar valores zerados
            df_banco = df_banco[(df_banco["CRÉDITO"] != 0) | (df_banco["DÉBITO"] != 0)]
            
            if df_banco.empty:
                continue
                
            # Ordenar transações
            df_banco = ordenar_transacoes(df_banco)
            
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
            
            # Cabeçalho do banco
            elements.append(Paragraph(f"Banco: {banco}", banco_style))
            elements.append(Spacer(1, 6))
            
            # Tabela de transações
            dados_tabela = [["Data", "Plano", "Descrição", "Entrada", "Saída"]]
            
            for _, row in df_banco.iterrows():
                data_str = date_input_br(row["data"])
                plano = str(row["plano"]) if "plano" in row and pd.notna(row["plano"]) else ""
                descricao = str(row["descricao"]) if "descricao" in row and pd.notna(row["descricao"]) else ""
                entrada = formatar_moeda(row["CRÉDITO"]) if row["CRÉDITO"] > 0 else ""
                saida = formatar_moeda(row["DÉBITO"]) if row["DÉBITO"] > 0 else ""
                
                dados_tabela.append([data_str, plano, descricao, entrada, saida])
            
            # Adicionar linha de soma
            dados_tabela.append(["", "", "Soma", formatar_moeda(credito_dia), formatar_moeda(debito_dia)])
            
            # Criar tabela
            if len(dados_tabela) > 1:
                col_widths = calcular_larguras_colunas_automaticas(dados_tabela[0], "movimento")
                tabela = Table(dados_tabela, colWidths=col_widths)
                estilo_tabela = TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (2,-1), 'LEFT'),
                    ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
                    ('FONTNAME', (3,1), (-1,-1), 'Courier'),
                    ('FONTNAME', (3,-1), (-1,-1), 'Courier-Bold'),
                    ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
                ])
                tabela.setStyle(estilo_tabela)
                elements.append(tabela)
            
            elements.append(Spacer(1, 8))
            
            # Resumo
            resumo_data = [
                [f"Saldo anterior......................................:", formatar_moeda(saldo_anterior)],
                [f"Total das entradas..................................:", formatar_moeda(credito_dia)],
                [f"Total das saídas ...................................:", formatar_moeda(debito_dia)],
                [f"Saldo Atual.........................................:", formatar_moeda(saldo_atual)]
            ]
            
            tabela_resumo = Table(resumo_data, colWidths=[200, 80])
            estilo_resumo = TableStyle([
                ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'),
                ('FONTNAME', (1,0), (1,-1), 'Courier'),
            ])
            tabela_resumo.setStyle(estilo_resumo)
            elements.append(tabela_resumo)
            
            elements.append(Spacer(1, 20))
        
        # Rodapé
        elements.append(Spacer(1, 9
        ))
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

def gerar_pdf_relatorio_analitico(data_inicio, data_fim, status_filtro, df):
    """Gera PDF para relatório analítico"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relatorio_analitico_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Estilos
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=12, leading=14)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], alignment=TA_LEFT,
                                    fontName=FONT_USADA, fontSize=9, leading=11)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=7, alignment=TA_RIGHT)
        
        elements = []
        
        # Título
        elements.append(Paragraph("RELATÓRIO ANALÍTICO", titulo_style))
        elements.append(Paragraph(f"Data: {date_input_br(date.today())}", normal_style))
        elements.append(Paragraph(f"Período: {date_input_br(data_inicio)} a {date_input_br(data_fim)}", normal_style))
        elements.append(Paragraph(f"Filtro: {status_filtro}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Filtrar valores zerados
        df = df[(df["CRÉDITO"] != 0) | (df["DÉBITO"] != 0)]
        
        if df.empty:
            st.warning("Nenhum dado com valores não zerados para gerar PDF.")
            return
        
        # Ordenar dados
        df = df.sort_values(by=["data", "descricao"]).reset_index(drop=True)
        
        # Tabela
        dados_tabela = [["Data", "relacao", "Subgrupo", "Plano", "Descrição", "Crédito", "Débito"]]
        
        for _, row in df.iterrows():
            data_str = date_input_br(row["data"])
            relacao = str(row["relacao"]) if "relacao" in row and pd.notna(row["relacao"]) else ""
            grupo = str(row["grupo"]) if "grupo" in row and pd.notna(row["grupo"]) else ""
            plano = str(row["plano"]) if "plano" in row and pd.notna(row["plano"]) else ""
            descricao = str(row["descricao"]) if "descricao" in row and pd.notna(row["descricao"]) else ""
            credito = formatar_moeda(row["CRÉDITO"])
            debito = formatar_moeda(row["DÉBITO"])
            
            dados_tabela.append([data_str, relacao, grupo, plano, descricao, credito, debito])
        
        # Calcular totais
        total_credito = df["CRÉDITO"].sum()
        total_debito = df["DÉBITO"].sum()
        saldo = total_credito - total_debito
        
        # Adicionar linha de totais
        dados_tabela.append(["", "", "", "", "TOTAIS:", formatar_moeda(total_credito), formatar_moeda(total_debito)])
        
        # Criar tabela com larguras automáticas
        col_widths = calcular_larguras_colunas_automaticas(dados_tabela[0], "analitico")
        tabela = Table(dados_tabela, colWidths=col_widths)
        estilo_tabela = TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (4,-1), 'LEFT'),
            ('ALIGN', (5,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (5,1), (-1,-1), 'Courier'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (5,-1), (-1,-1), 'Courier-Bold'),
        ])
        tabela.setStyle(estilo_tabela)
        elements.append(tabela)
        
        elements.append(Spacer(1, 12))
        
        # Resumo
        elements.append(Paragraph(f"Crédito: {formatar_moeda(total_credito)}", normal_style))
        elements.append(Paragraph(f"Débito: {formatar_moeda(total_debito)}", normal_style))
        elements.append(Paragraph(f"Saldo: {formatar_moeda(saldo)}", normal_style))
        
        # Rodapé
        elements.append(Spacer(1, 9
        ))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        
        # Construir PDF
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        
        # Botão de download
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar PDF - Relatório Analítico", 
                data=f.read(), 
                file_name=filename, 
                mime="application/pdf", 
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")

def gerar_pdf_relatorio_sintetico(data_inicio, data_fim, status_filtro, df):
    """Gera PDF para relatório sintético - CORRIGIDO"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relatorio_sintetico_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Estilos
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=12, leading=14)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], alignment=TA_LEFT,
                                    fontName=FONT_USADA, fontSize=9, leading=11)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=7, alignment=TA_RIGHT)
        
        elements = []
        
        # Título
        elements.append(Paragraph("RELATÓRIO SINTÉTICO", titulo_style))
        elements.append(Paragraph(f"Data: {date_input_br(date.today())}", normal_style))
        elements.append(Paragraph(f"Período: {date_input_br(data_inicio)} a {date_input_br(data_fim)}", normal_style))
        elements.append(Paragraph(f"Filtro: {status_filtro}", normal_style))
        elements.append(Spacer(1, 12))
        
        # DEBUG: Verificar dados recebidos
        st.sidebar.info(f"Total registros: {len(df)}")
        if not df.empty:
            st.sidebar.info(f"Colunas: {df.columns.tolist()}")
        
        # CORREÇÃO: Filtrar para desconsiderar "Transferências" no subgrupo
        df_sem_transferencias = df[df['subgrupo'] != 'Transferências'].copy()
        
        # Filtrar valores zerados
        df_filtrado = df_sem_transferencias[(df_sem_transferencias["CRÉDITO"] != 0) | (df_sem_transferencias["DÉBITO"] != 0)].copy()
        
        if df_filtrado.empty:
            st.warning("Nenhum dado com valores não zerados para gerar PDF.")
            return
        
        # DEBUG: Verificar após filtro
        st.sidebar.info(f"Após filtro: {len(df_filtrado)} registros")
        
        # CORREÇÃO: Verificar se a coluna 'subgrupo' existe
        coluna_agrupamento = "subgrupo" if "subgrupo" in df_filtrado.columns else "Subgrupo"
        
        # Agrupar dados SOMENTE por subgrupo
        df_agrupado = df_filtrado.groupby([coluna_agrupamento], dropna=False).agg({
            "CRÉDITO": "sum",
            "DÉBITO": "sum"
        }).reset_index()
        
        # DEBUG: Verificar agrupamento
        st.sidebar.info(f"Após agrupamento: {len(df_agrupado)} subgrupos")
        
        # CORREÇÃO: Ordenar PRIMEIRO por Crédito (decrescente), DEPOIS por Débito (decrescente)
        df_agrupado = df_agrupado.sort_values(
            by=['CRÉDITO', 'DÉBITO'], 
            ascending=[False, False]  # Maiores créditos primeiro, depois maiores débitos
        )
        
        # Tabela - mantém a ordem de exibição: Subgrupo, Crédito, Débito
        dados_tabela = [["Subgrupo", "Crédito", "Débito"]]
        
        for _, row in df_agrupado.iterrows():
            subgrupo_valor = str(row[coluna_agrupamento]) if pd.notna(row[coluna_agrupamento]) else "NÃO INFORMADO"
            credito = formatar_moeda(row["CRÉDITO"])
            debito = formatar_moeda(row["DÉBITO"])
            dados_tabela.append([subgrupo_valor, credito, debito])
        
        # Calcular totais
        total_credito = df_agrupado["CRÉDITO"].sum()
        total_debito = df_agrupado["DÉBITO"].sum()
        saldo = total_credito - total_debito
        
        # Adicionar linha de totais
        dados_tabela.append(["TOTAIS:", formatar_moeda(total_credito), formatar_moeda(total_debito)])
        
        # Ajustar larguras das colunas para página vertical
        col_widths = [300, 100, 100]  # Subgrupo mais larga, Crédito, Débito
        
        tabela = Table(dados_tabela, colWidths=col_widths)
        estilo_tabela = TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (1,1), (-1,-1), 'Courier'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (1,-1), (-1,-1), 'Courier-Bold'),
        ])
        tabela.setStyle(estilo_tabela)
        elements.append(tabela)
        
        elements.append(Spacer(1, 12))
        
        # Resumo
        elements.append(Paragraph(f"Crédito: {formatar_moeda(total_credito)}", normal_style))
        elements.append(Paragraph(f"Débito: {formatar_moeda(total_debito)}", normal_style))
        elements.append(Paragraph(f"Saldo: {formatar_moeda(saldo)}", normal_style))
        
        # Rodapé
        elements.append(Spacer(1, 9))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        
        # Construir PDF
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        
        # Botão de download
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar PDF - Relatório Sintético", 
                data=f.read(), 
                file_name=filename, 
                mime="application/pdf", 
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        st.error(f"Detalhes do erro: {str(e)}")

def gerar_pdf_relacao_analitico(data_inicio, data_fim, status_filtro, df):
    """Gera PDF para relação analítico"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relacao_analitico_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Estilos
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=12, leading=14)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], alignment=TA_LEFT,
                                    fontName=FONT_USADA, fontSize=9, leading=11)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=7, alignment=TA_RIGHT)
        
        elements = []
        
        # Título
        elements.append(Paragraph("RELAÇÃO ANALÍTICO", titulo_style))
        elements.append(Paragraph(f"Data: {date_input_br(date.today())}", normal_style))
        elements.append(Paragraph(f"Período: {date_input_br(data_inicio)} a {date_input_br(data_fim)}", normal_style))
        elements.append(Paragraph(f"Filtro: {status_filtro}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Filtrar valores zerados
        df = df[(df["CRÉDITO"] != 0) | (df["DÉBITO"] != 0)]
        
        if df.empty:
            st.warning("Nenhum dado com valores não zerados para gerar PDF.")
            return
        
        # Ordenar dados
        df = df.sort_values(by=["data", "descricao"]).reset_index(drop=True)
        
        # Tabela - Ajuste das colunas
        dados_tabela = [["Data", "Relação", "Plano", "Descrição", "Crédito", "Débito"]]
        
        for _, row in df.iterrows():
            data_str = date_input_br(row["data"])
            relacao = str(row["relacao"]) if "relacao" in row and pd.notna(row["relacao"]) else ""
            plano = str(row["plano"]) if "plano" in row and pd.notna(row["plano"]) else ""
            descricao = str(row["descricao"]) if "descricao" in row and pd.notna(row["descricao"]) else ""
            credito = formatar_moeda(row["CRÉDITO"])
            debito = formatar_moeda(row["DÉBITO"])
            
            dados_tabela.append([data_str, relacao, plano, descricao, credito, debito])
        
        # Calcular totais
        total_credito = df["CRÉDITO"].sum()
        total_debito = df["DÉBITO"].sum()
        saldo = total_credito - total_debito
        
        # Adicionar linha de totais - CORRIGIDO: número de colunas
        dados_tabela.append(["", "", "", "TOTAIS:", formatar_moeda(total_credito), formatar_moeda(total_debito)])
        
        # Definir larguras das colunas manualmente para melhor ajuste
        # Ajuste estas proporções conforme necessário
        larguras_colunas = [
            60,  # Data
            180,  # Relação
            80,  # Plano
            180, # Descrição (mais larga)
            75,  # Crédito
            75   # Débito
        ]
        
        # Ou use a função automática se preferir
        # larguras_colunas = calcular_larguras_colunas_automaticas(dados_tabela[0], "analitico")
        
        tabela = Table(dados_tabela, colWidths=larguras_colunas)
        estilo_tabela = TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (3,-1), 'LEFT'),      # Colunas textuais alinhadas à esquerda
            ('ALIGN', (4,0), (-1,-1), 'RIGHT'),    # Colunas numéricas alinhadas à direita
            ('FONTNAME', (4,1), (-1,-1), 'Courier'), # Fonte monoespaçada para valores
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (4,-1), (-1,-1), 'Courier-Bold'),
            ('FONTSIZE', (0,-1), (-1,-1), 9),      # Fonte um pouco maior para totais
        ])
        tabela.setStyle(estilo_tabela)
        elements.append(tabela)
        
        elements.append(Spacer(1, 12))
        
        # Resumo
        elements.append(Paragraph(f"Crédito: {formatar_moeda(total_credito)}", normal_style))
        elements.append(Paragraph(f"Débito: {formatar_moeda(total_debito)}", normal_style))
        elements.append(Paragraph(f"Saldo: {formatar_moeda(saldo)}", normal_style))
        
        # Rodapé
        elements.append(Spacer(1, 9))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        
        # Construir PDF
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        
        # Botão de download
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar PDF - Relação Analítico", 
                data=f.read(), 
                file_name=filename, 
                mime="application/pdf", 
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")

def gerar_pdf_relacao_sintetico(data_inicio, data_fim, status_filtro, df):
    """Gera PDF para relação sintético - CORRIGIDO"""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relacao_sintetico_{timestamp}.pdf"
        caminho_pdf = os.path.join(PASTA_RELATORIOS, filename)
        
        doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Estilos
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
                                    fontName=FONT_USADA, fontSize=12, leading=14)
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], alignment=TA_LEFT,
                                    fontName=FONT_USADA, fontSize=9, leading=11)
        rodape_style = ParagraphStyle('Rodape', fontName=FONT_USADA, fontSize=7, alignment=TA_RIGHT)
        
        elements = []
        
        # Título
        elements.append(Paragraph("RELAÇÃO SINTÉTICO", titulo_style))
        elements.append(Paragraph(f"Data: {date_input_br(date.today())}", normal_style))
        elements.append(Paragraph(f"Período: {date_input_br(data_inicio)} a {date_input_br(data_fim)}", normal_style))
        elements.append(Paragraph(f"Filtro: {status_filtro}", normal_style))
        elements.append(Spacer(1, 12))
        
        # DEBUG: Verificar dados recebidos
        st.sidebar.info(f"Total registros: {len(df)}")
        if not df.empty:
            st.sidebar.info(f"Colunas: {df.columns.tolist()}")
            # CORREÇÃO: Verificar coluna 'relacao' em vez de 'relacao'
            if 'relacao' in df.columns:
                st.sidebar.info(f"Relações únicas: {df['relacao'].nunique()}")
        
        # Filtrar valores zerados
        df_filtrado = df[(df["CRÉDITO"] != 0) | (df["DÉBITO"] != 0)].copy()
        
        if df_filtrado.empty:
            st.warning("Nenhum dado com valores não zerados para gerar PDF.")
            return
        
        # DEBUG: Verificar após filtro
        st.sidebar.info(f"Após filtro: {len(df_filtrado)} registros")
        
        # CORREÇÃO: Agrupar por 'relacao' em vez de 'relacao'
        coluna_agrupamento = "relacao" if "relacao" in df_filtrado.columns else "relacao"
        
        # Agrupar dados SOMENTE por relacao (conforme solicitado)
        df_agrupado = df_filtrado.groupby([coluna_agrupamento], dropna=False).agg({
            "CRÉDITO": "sum",
            "DÉBITO": "sum"
        }).reset_index()
        
        # DEBUG: Verificar agrupamento
        st.sidebar.info(f"Após agrupamento: {len(df_agrupado)} relações")
        
        # Ordenar por relação (Receita primeiro, depois Despesas)
        df_agrupado = ordenar_por_relacao(df_agrupado)
        
        # Tabela
        dados_tabela = [["relacao", "Crédito", "Débito"]]
        
        for _, row in df_agrupado.iterrows():
            # CORREÇÃO: Usar coluna_agrupamento em vez de "relacao" fixo
            relacao_valor = str(row[coluna_agrupamento]) if pd.notna(row[coluna_agrupamento]) else "NÃO INFORMADO"
            credito = formatar_moeda(row["CRÉDITO"])
            debito = formatar_moeda(row["DÉBITO"])
            dados_tabela.append([relacao_valor, credito, debito])
        
        # Calcular totais
        total_credito = df_agrupado["CRÉDITO"].sum()
        total_debito = df_agrupado["DÉBITO"].sum()
        saldo = total_credito - total_debito
        
        # Adicionar linha de totais
        dados_tabela.append(["TOTAIS:", formatar_moeda(total_credito), formatar_moeda(total_debito)])
        
        # Criar tabela com larguras automáticas
        col_widths = calcular_larguras_colunas_automaticas(dados_tabela[0], "rel_sintetico")
        tabela = Table(dados_tabela, colWidths=col_widths)
        estilo_tabela = TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_USADA),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (1,1), (-1,-1), 'Courier'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (1,-1), (-1,-1), 'Courier-Bold'),
        ])
        tabela.setStyle(estilo_tabela)
        elements.append(tabela)
        
        elements.append(Spacer(1, 12))
        
        # Resumo
        elements.append(Paragraph(f"Crédito: {formatar_moeda(total_credito)}", normal_style))
        elements.append(Paragraph(f"Débito: {formatar_moeda(total_debito)}", normal_style))
        elements.append(Paragraph(f"Saldo: {formatar_moeda(saldo)}", normal_style))
        
        # Rodapé
        elements.append(Spacer(1, 9))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", rodape_style))
        
        # Construir PDF
        doc.build(elements)
        st.success(f"✅ PDF gerado em: {caminho_pdf}")
        
        # Botão de download
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar PDF - relacao Sintético", 
                data=f.read(), 
                file_name=filename, 
                mime="application/pdf", 
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        st.error(f"Detalhes do erro: {str(e)}")

# -------------------------
# RELATÓRIOS
# -------------------------
def rel_analitico():
    styled_subheader("📑 Relatório Analítico", "16px", "#FFFFFF")
    aplicar_estilo_unificado()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_inicio = st.date_input(
            "Data inicial:",
            value=date.today(),
            key="analitico_data_inicio",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col2:
        data_fim = st.date_input(
            "Data final:",
            value=date.today(),
            key="analitico_data_fim",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="analitico_status_select")    
               
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    # Cabeçalho com datas
    st.markdown(f'<div class="header-relatorio"><b>Data do Relatório:</b> {date_input_br(date.today())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Período:</b> {date_input_br(data_inicio)} a {date_input_br(data_fim)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Filtro:</b> {status_filtro}</div>', unsafe_allow_html=True)
    
    # Tabela (já filtra valores zerados automaticamente)
    df_ordenado = display_tabela_unificada(df, "analitico")
    
    # Resumo
    total_credito = df_ordenado["CRÉDITO"].sum() if not df_ordenado.empty else 0
    total_debito = df_ordenado["DÉBITO"].sum() if not df_ordenado.empty else 0
    saldo = total_credito - total_debito
    
    st.markdown("---")
    st.markdown("### Resumo")
    display_resumo_movimento(0, total_credito, total_debito, saldo)
    
    # Botão PDF
    if st.button("📄 Gerar PDF - Relatório Analítico", key="pdf_analitico"):
        gerar_pdf_relatorio_analitico(data_inicio, data_fim, status_filtro, df)

def rel_sintetico():
    styled_subheader("📊 Relatório Sintético", "16px", "#FFFFFF")
    aplicar_estilo_unificado()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_inicio = st.date_input(
            "Data inicial:",
            value=date.today(),
            key="sintetico_data_inicio",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col2:
        data_fim = st.date_input(
            "Data final:",
            value=date.today(),
            key="sintetico_data_fim",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="sintetico_status_select")  

    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    # Cabeçalho com datas
    st.markdown(f'<div class="header-relatorio"><b>Data do Relatório:</b> {date_input_br(date.today())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Período:</b> {date_input_br(data_inicio)} a {date_input_br(data_fim)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Filtro:</b> {status_filtro}</div>', unsafe_allow_html=True)
    
    # CORREÇÃO: Usar display_tabela_unificada em vez de agrupamento manual
    df_ordenado = display_tabela_unificada(df, "rel_sintetico")
    
    # Resumo BASEADO NOS DADOS AGRUPADOS
    if not df_ordenado.empty:
        total_credito = df_ordenado["CRÉDITO"].sum()
        total_debito = df_ordenado["DÉBITO"].sum()
        saldo = total_credito - total_debito
    else:
        total_credito = 0
        total_debito = 0
        saldo = 0
    
    st.markdown("---")
    st.markdown("### Resumo")
    display_resumo_movimento(0, total_credito, total_debito, saldo)
    
    # Botão PDF
    if st.button("📄 Gerar PDF - Relatório Sintético", key="pdf_sintetico"):
        gerar_pdf_relatorio_sintetico(data_inicio, data_fim, status_filtro, df_ordenado)

def relacao_analitico():
    styled_subheader("📑 relacao Analítico", "16px", "#FFFFFF")
    aplicar_estilo_unificado()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_inicio = st.date_input(
            "Data inicial:",
            value=date.today(),
            key="analitico_data_inicio",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col2:
        data_fim = st.date_input(
            "Data final:",
            value=date.today(),
            key="analitico_data_fim",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="analitico_status_select")  
    
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    # Cabeçalho com datas
    st.markdown(f'<div class="header-relatorio"><b>Data do Relatório:</b> {date_input_br(date.today())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Período:</b> {date_input_br(data_inicio)} a {date_input_br(data_fim)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Filtro:</b> {status_filtro}</div>', unsafe_allow_html=True)
    
    # Tabela (já filtra valores zerados automaticamente)
    df_ordenado = display_tabela_unificada(df, "analitico")
    
    # Resumo
    total_credito = df_ordenado["CRÉDITO"].sum() if not df_ordenado.empty else 0
    total_debito = df_ordenado["DÉBITO"].sum() if not df_ordenado.empty else 0
    saldo = total_credito - total_debito
    
    st.markdown("---")
    st.markdown("### Resumo")
    display_resumo_movimento(0, total_credito, total_debito, saldo)
    
    # Botão PDF
    if st.button("📄 Gerar PDF - relacao Analítico", key="pdf_rel_analitico"):
        gerar_pdf_relacao_analitico(data_inicio, data_fim, status_filtro, df)

def relacao_sintetico():
    styled_subheader("📊 relacao Sintético", "16px", "#FFFFFF")
    aplicar_estilo_unificado()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_inicio = st.date_input(
            "Data inicial:",
            value=date.today(),
            key="analitico_data_inicio",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col2:
        data_fim = st.date_input(
            "Data final:",
            value=date.today(),
            key="analitico_data_fim",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="analitico_status_select")  
    
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    # Cabeçalho com datas
    st.markdown(f'<div class="header-relatorio"><b>Data do Relatório:</b> {date_input_br(date.today())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Período:</b> {date_input_br(data_inicio)} a {date_input_br(data_fim)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Filtro:</b> {status_filtro}</div>', unsafe_allow_html=True)
    
    # Tabela - AGORA COM AGRUPAMENTO POR "relacao"
    df_ordenado = display_tabela_unificada(df, "sintetico")
    
    # Resumo BASEADO NOS DADOS AGRUPADOS
    if not df_ordenado.empty:
        # Para o resumo na tela, usar os dados já agrupados e ordenados
        total_credito = df_ordenado["CRÉDITO"].sum()
        total_debito = df_ordenado["DÉBITO"].sum()
        saldo = total_credito - total_debito
    else:
        total_credito = 0
        total_debito = 0
        saldo = 0
    
    st.markdown("---")
    st.markdown("### Resumo")
    display_resumo_movimento(0, total_credito, total_debito, saldo)
    
    # Botão PDF
    if st.button("📄 Gerar PDF - relacao Sintético", key="pdf_rel_sintetico"):
        gerar_pdf_relacao_sintetico(data_inicio, data_fim, status_filtro, df_ordenado)

def mov_caixa_banco():
    styled_subheader("🏦 Movimento Diário - Caixa/Banco", "16px", "#FFFFFF")
    aplicar_estilo_unificado()
    
    col1, col2 = st.columns(2)
    with col1:
        data_relatorio = st.date_input("Data do relatório:", value=date.today(), key="mov_caixa_data", format="DD/MM/YYYY")
    with col2:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="mov_caixa_status")
            
    df = carregar_dados_financeiros(data_relatorio, data_relatorio, status_filtro)
    if df.empty:
        st.warning("Nenhum movimento encontrado para esta data.")
        return
    
    if "banco" not in df.columns:
        df["banco"] = "Carteira"
    df["banco"] = df["banco"].fillna("Carteira")
    
    # Cabeçalho com data específica para movimento diário
    st.markdown(f'<div class="header-relatorio"><b>Data do Relatório:</b> {date_input_br(date.today())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Data do Movimento:</b> {date_input_br(data_relatorio)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-relatorio"><b>Filtro:</b> {status_filtro}</div>', unsafe_allow_html=True)
    
    # Para cada banco
    bancos = sorted(df["banco"].unique())
    for banco in bancos:
        df_banco = df[df["banco"] == banco].copy()
        
        # Calcular saldos
        data_anterior = data_relatorio - pd.Timedelta(days=1)
        df_historico = carregar_dados_financeiros(date(1900, 1, 1), data_anterior, "Pago")
        
        saldo_anterior = 0
        if not df_historico.empty and "banco" in df_historico.columns:
            df_historico_banco = df_historico[df_historico["banco"] == banco]
            saldo_anterior = df_historico_banco["CRÉDITO"].sum() - df_historico_banco["DÉBITO"].sum()
        
        credito_dia = df_banco["CRÉDITO"].sum()
        debito_dia = df_banco["DÉBITO"].sum()
        saldo_atual = saldo_anterior + credito_dia - debito_dia
        
        # Cabeçalho do banco
        st.markdown(f'<div class="header-relatorio"><b>Banco:</b> {banco}</div>', unsafe_allow_html=True)
        
        # Tabela (já filtra valores zerados automaticamente)
        df_ordenado = display_tabela_unificada(df_banco, "movimento")
        
        # Resumo ajustado
        display_resumo_movimento(saldo_anterior, credito_dia, debito_dia, saldo_atual)
        
        st.markdown("")  # Espaçamento
    
    # Botão PDF
    if st.button("📄 Gerar PDF - Movimento Diário", key="pdf_mov_caixa"):
        bancos = sorted(df["banco"].unique())
        gerar_pdf_movimento_caixa(data_relatorio, status_filtro, df, bancos)

def relatorio_categoria():
    styled_subheader("📊 Relatório por Categoria", "16px", "#000000")
    aplicar_estilo_unificado()

    # Entradas de filtro
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_inicio = st.date_input(
            "Data inicial:",
            value=date.today(),
            key="analitico_data_inicio",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col2:
        data_fim = st.date_input(
            "Data final:",
            value=date.today(),
            key="analitico_data_fim",  # ← VÍRGULA ADICIONADA
            format="DD/MM/YYYY"
        )
    with col3:
        status_filtro = st.selectbox("Status", ["Todos", "Pago", "Aberto"], key="analitico_status_select")  

    # Carregar dados
    df = carregar_dados_financeiros(data_inicio, data_fim, status_filtro)
    if df.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    # Coluna Subgrupo
    for nome in ["Subgrupo", "subgrupo", "Subrupo", "subrupo"]:
        if nome in df.columns:
            df = df.rename(columns={nome: "Subgrupo"})
            break
    else:
        st.error("❌ A coluna 'Subgrupo' não foi encontrada no Banco.")
        st.write("📌 Colunas retornadas do banco:", df.columns.tolist())
        return

    # CORREÇÃO: Filtrar para remover "Transferencias"
    # Primeiro, normalizar os valores da coluna Subgrupo
    df["Subgrupo"] = df["Subgrupo"].str.strip().str.lower()
    
    # Filtrar para remover transferências (considerando variações de escrita)
    transferencias_keywords = ["transferencia", "transferências", "transfer", "transf"]
    
    # Criar máscara para excluir transferências
    mask_transferencias = df["Subgrupo"].str.contains('|'.join(transferencias_keywords), case=False, na=False)
    
    # Aplicar filtro - manter apenas os registros que NÃO são transferências
    df = df[~mask_transferencias]
    
    # Verificar se ainda há dados após o filtro
    if df.empty:
        st.warning("Nenhum dado encontrado após filtrar transferências.")
        return

    # Padronizar categoria
    df["categoria"] = df["categoria"].str.strip().str.upper()
    df["categoria"] = df["categoria"].replace({
        "CRÉDITO": "Crédito",
        "CREDITO": "Crédito",
        "DÉBITO": "Débito",
        "DEBITO": "Débito"
    })

    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df[(df['data'].dt.date >= data_inicio) & (df['data'].dt.date <= data_fim)]

    # Pivot table
    df_pivot = pd.pivot_table(
        df,
        values='valor',
        index='Subgrupo',
        columns='categoria',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    for col in ["Crédito", "Débito"]:
        if col not in df_pivot.columns:
            df_pivot[col] = 0

    # CORREÇÃO: Separar créditos e débitos e ordenar individualmente
    df_credito = df_pivot[df_pivot["Crédito"] != 0].copy()
    df_debito = df_pivot[df_pivot["Débito"] != 0].copy()
    
    # Ordenar créditos em ordem ascendente
    df_credito = df_credito.sort_values("Crédito", ascending=True)
    # Ordenar débitos em ordem ascendente  
    df_debito = df_debito.sort_values("Débito", ascending=True)
    
    # Juntar os dados: créditos primeiro, depois débitos
    df_final = pd.concat([df_credito, df_debito], ignore_index=True)

    # CORREÇÃO: Formatação específica para o formato desejado
    df_display = df_final.copy()
    
    # Formatar crédito - R$ à esquerda, valor alinhado
    df_display["Crédito"] = df_display["Crédito"].apply(
        lambda x: f" R$ {x:,.2f} ".replace(',', 'X').replace('.', ',').replace('X', '.') if x != 0 else ""
    )
    
    # Formatar débito - R$ à esquerda, valor alinhado  
    df_display["Débito"] = df_display["Débito"].apply(
        lambda x: f" R$ {x:,.2f} ".replace(',', 'X').replace('.', ',').replace('X', '.') if x != 0 else ""
    )

    # Exibir tabela expandida
    st.subheader("relacao por Subgrupo (Transferências Excluídas)")
    st.dataframe(df_display[["Subgrupo", "Crédito", "Débito"]], use_container_width=True)

    # Gráficos horizontais com tamanho menor
    exibir_grafico_horizontal(df_credito, "Crédito", "#4CAF50", fontsize=11)
    exibir_grafico_horizontal(df_debito, "Débito", "#ff6b6b", fontsize=11)

    # Totais
    total_credito = df_credito["Crédito"].sum()
    total_debito = df_debito["Débito"].sum()
    st.info(f"**Total Crédito:** R$ {total_credito:,.2f} | **Total Débito:** R$ {total_debito:,.2f}")

    # Botão PDF
    if st.button("📄 Gerar PDF"):
        gerar_pdf_relatorio_categoria(data_inicio, data_fim, status_filtro, df_final, df_credito, df_debito)

# ---------- Gráficos horizontais ----------

def exibir_grafico_horizontal(df, coluna_valor, cor, fontsize=11):  # Alterado para 11px padrão
    if coluna_valor not in df.columns:
        return

    df_plot = df[df[coluna_valor] != 0].copy()
    if df_plot.empty:
        st.info(f"ℹ️ Não há {coluna_valor.lower()} para exibir")
        return

    df_plot = df_plot.sort_values(coluna_valor, ascending=True)
    num_barras = len(df_plot)
    altura = max(3, 0.5 * num_barras)

    fig, ax = plt.subplots(figsize=(8, altura))
    ax.barh(df_plot['Subgrupo'], df_plot[coluna_valor], color=cor, alpha=0.8, height=0.6)

    for i, (valor, label) in enumerate(zip(df_plot[coluna_valor], df_plot['Subgrupo'])):
        ax.text(valor + (valor*0.01), i,
                f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                va='center', fontsize=fontsize)  # Usando o fontsize parametrizado

    ax.set_xlabel("Valor (R$)", fontsize=fontsize)
    ax.tick_params(axis='y', labelsize=fontsize)
    ax.tick_params(axis='x', labelsize=fontsize)
    ax.grid(axis='x', alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# ---------- Gerar PDF com gráficos ----------

def gerar_pdf_relatorio_categoria(data_inicio, data_fim, status_filtro, df_final, df_credito, df_debito):
    """Gera PDF do relatório por categoria no formato específico solicitado."""
    try:
        # Criar PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=10)

        # Cabeçalho
        pdf.cell(0, 10, f"Data do Relatório: {date_input_br(date.today())}", ln=True)
        pdf.cell(0, 10, f"Período: {date_input_br(data_inicio)} a {date_input_br(data_fim)}", ln=True)
        pdf.cell(0, 10, f"Filtro: {status_filtro}", ln=True)
        pdf.ln(5)

        # Título
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Relatório por Categoria", ln=True)
        pdf.ln(5)

        # Cabeçalho da tabela
        pdf.set_font("Arial", 'B', 9)
        col_widths = [80, 55, 55]  # Larguras ajustadas
        x_position = 10
        
        pdf.set_x(x_position)
        pdf.cell(col_widths[0], 8, "Subgrupo", border=1, align='C')
        pdf.cell(col_widths[1], 8, "Crédito", border=1, align='C')
        pdf.cell(col_widths[2], 8, "Débito", border=1, align='C')
        pdf.ln()

        # Dados da tabela - CORREÇÃO: Formato específico
        pdf.set_font("Arial", size=9)
        
        # Primeiro os créditos (valores positivos)
        for _, row in df_credito.iterrows():
            pdf.set_x(x_position)
            grupo_texto = str(row["Subgrupo"])
            if len(grupo_texto) > 25:
                grupo_texto = grupo_texto[:22] + "..."
            pdf.cell(col_widths[0], 6, grupo_texto, border=1, align='L')
            
            # Formatar crédito
            credito_valor = row["Crédito"]
            credito_texto = f" R$ {credito_valor:>10,.2f} ".replace(',', 'X').replace('.', ',').replace('X', '.')
            pdf.cell(col_widths[1], 6, credito_texto, border=1, align="R")
            pdf.cell(col_widths[2], 6, "", border=1, align="R")  # Débito vazio
            pdf.ln()
        
        # Depois os débitos (valores positivos)
        for _, row in df_debito.iterrows():
            pdf.set_x(x_position)
            grupo_texto = str(row["Subgrupo"])
            if len(grupo_texto) > 25:
                grupo_texto = grupo_texto[:22] + "..."
            pdf.cell(col_widths[0], 6, grupo_texto, border=1, align='L')
            
            # Crédito vazio
            pdf.cell(col_widths[1], 6, "", border=1, align="R")
            
            # Formatar débito
            debito_valor = row["Débito"]
            debito_texto = f" R$ {debito_valor:>10,.2f} ".replace(',', 'X').replace('.', ',').replace('X', '.')
            pdf.cell(col_widths[2], 6, debito_texto, border=1, align="R")
            pdf.ln()

        # Resumo
        pdf.ln(8)
        total_credito = df_credito["Crédito"].sum()
        total_debito = df_debito["Débito"].sum()
        saldo = total_credito - total_debito

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, "RESUMO", ln=True)
        pdf.set_font("Arial", size=9)
        pdf.cell(0, 6, f"Total Crédito: R$ {total_credito:>12,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), ln=True)
        pdf.cell(0, 6, f"Total Débito: R$ {total_debito:>12,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), ln=True)
        pdf.cell(0, 6, f"Saldo: R$ {saldo:>12,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), ln=True)

        # --- Gráficos com fonte menor ---
        def gerar_grafico_png(df_plot, coluna_valor, cor, titulo):
            if df_plot.empty:
                return None

            df_plot = df_plot.sort_values(coluna_valor, ascending=True)
            altura = max(3, 0.4 * len(df_plot))
            fig, ax = plt.subplots(figsize=(8, altura), dpi=100)
            
            ax.barh(df_plot['Subgrupo'], df_plot[coluna_valor], color=cor, alpha=0.8, height=0.6)

            for i, (valor, label) in enumerate(zip(df_plot[coluna_valor], df_plot['Subgrupo'])):
                ax.text(valor + (valor * 0.01), i,
                        f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                        va='center', fontsize=8)

            ax.set_xlabel("Valor (R$)", fontsize=8)
            ax.set_title(titulo, fontsize=10)
            ax.tick_params(axis='y', labelsize=8)
            ax.tick_params(axis='x', labelsize=8)
            ax.grid(axis='x', alpha=0.2)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()

            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            fig.savefig(tmp_file.name, bbox_inches='tight', dpi=150)
            plt.close(fig)
            return tmp_file.name

        # Gerar gráficos
        grafico_credito = gerar_grafico_png(df_credito, "Crédito", "#4CAF50", "Crédito por Subgrupo")
        grafico_debito = gerar_grafico_png(df_debito, "Débito", "#ff6b6b", "Débito por Subgrupo")

        # Adicionar gráficos ao PDF
        if grafico_credito:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 10, "Gráfico de Crédito", ln=True, align='C')
            pdf.image(grafico_credito, x=15, y=25, w=180)
            os.remove(grafico_credito)

        if grafico_debito:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 10, "Gráfico de Débito", ln=True, align='C')
            pdf.image(grafico_debito, x=15, y=25, w=180)
            os.remove(grafico_debito)

        # Gerar PDF final
        pdf_output = pdf.output(dest='S').encode('latin-1', errors='replace')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relatorio_categoria_{timestamp}.pdf"

        st.success("✅ PDF gerado com sucesso!")
        st.download_button(
            label="📥 Download PDF",
            data=pdf_output,
            file_name=filename,
            mime="application/pdf",
            key=f"download_pdf_{timestamp}"
        )

    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")

def adicionar_graficos_simples_pdf(pdf, df, coluna_grupo, coluna_credito, coluna_debito):
    # Cria gráficos simples de Crédito e Débito lado a lado
    for coluna, cor, titulo in [(coluna_credito, '#4CAF50', 'Crédito'), (coluna_debito, '#ff6b6b', 'Débito')]:
        df_plot = df[df[coluna] != 0].sort_values(coluna, ascending=True)
        if df_plot.empty:
            continue

        fig, ax = plt.subplots(figsize=(6, max(3, 0.5*len(df_plot))))
        ax.barh(df_plot[coluna_grupo], df_plot[coluna], color=cor, alpha=0.8, height=0.6)
        for i, (valor, label) in enumerate(zip(df_plot[coluna], df_plot[coluna_grupo])):
            ax.text(valor + (valor*0.01), i,
                    f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    va='center', fontsize=9)
        ax.set_xlabel("Valor (R$)", fontsize=9)
        ax.tick_params(axis='y', labelsize=8)
        ax.tick_params(axis='x', labelsize=8)
        ax.grid(axis='x', alpha=0.2)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()

        # Salvar em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpfile:
            fig.savefig(tmpfile.name, format='png')
            pdf.image(tmpfile.name, w=pdf.w/2 - 20)  # ajustar largura
            plt.close(fig)
            os.remove(tmpfile.name)
# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    st.title("📈 Sistema de Relatórios Financeiros")
    # VERIFICAÇÃO DO BANCO DE DADOS
    banco_ok = verificar_banco_dados()
    
    if not banco_ok:
        st.error("""
        ⚠️ **Problema com o banco de dados**
        
        Para desenvolvimento:
        - Certifique-se de que o arquivo `nps_financeiro.db` está em `C:\\NPS-FIN\\dist\\`
        
        Para produção:  
        - O banco deve estar na mesma pasta do executável
        """)
        st.stop()

    tabs = st.tabs([
        "Relatório por Categoria",
        "Relatório Analítico", 
        "Relatório Sintético", 
        "relacao Analítico", 
        "relacao Sintético",
        "Movimento Diário"
    ])
    
    with tabs[0]: 
        relatorio_categoria()
    with tabs[1]: 
        rel_analitico()
    with tabs[2]: 
        rel_sintetico()
    with tabs[3]: 
        relacao_analitico()
    with tabs[4]: 
        relacao_sintetico()
    with tabs[5]: 
        mov_caixa_banco()