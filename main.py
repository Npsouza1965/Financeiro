import os
import sys
import warnings
import base64
import streamlit as st

# Garante que os submódulos sejam encontrados
base_path = os.path.dirname(__file__)
if base_path not in sys.path:
    sys.path.append(base_path)

warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

import financeiro
import clientes
import fornecedores
import planos
import Relatorio
import usuarios

print("[INFO] main.py foi iniciado com sucesso!")

st.set_page_config(page_title="Financeiro", page_icon="📊", layout="wide")

def resource_path(relative_path: str) -> str:
    if getattr(sys, "_MEIPASS", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

sys.path.append(resource_path("modules"))

log_file = resource_path("erro_log.txt")
try:
    log = open(log_file, "a", encoding="utf-8")
    sys.stdout = log
    sys.stderr = log
    print("\n--- Nova execução ---")
except Exception as e:
    print(f"Erro ao abrir log: {e}")

def set_login_background(filename="Fundo.png"):
    path = resource_path(filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
        }}
        </style>
        """, unsafe_allow_html=True)

def set_background_static(relative_path):
    path = resource_path("c:\\projetos\\static\\tela_fundo_azul.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
        }}
        </style>
        """, unsafe_allow_html=True)

def main_app():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None

    if not st.session_state["authenticated"]:
        set_login_background("c:\\projetos\\Fundo.png")
        usuarios.login_screen()
        return

    st.sidebar.title(f"📌 Menu - Usuário: {st.session_state['user']}")
    menu = st.sidebar.radio(
        "Navegação",
        ["Financeiro", "Clientes", "Fornecedores", "Planos",
         "Relatórios", "Cadastro de Usuário", "Sair"]
    )

    if menu == "Financeiro":
        financeiro.exibir_financeiro()
        set_background_static("c:\\projetos\\static\\tela_fundo_azul.png")
    elif menu == "Clientes":
        clientes.exibir_clientes()
        set_background_static("c:\\projetos\\static\\tela_fundo_azul.png")
    elif menu == "Fornecedores":
        fornecedores.exibir_fornecedores()
        set_background_static("c:\\projetos\\static\\tela_fundo_azul.png")
    elif menu == "Planos":
        planos.exibir_conta_planos()
        set_background_static("c:\\projetos\\static\\tela_fundo_azul.png")
    elif menu == "Relatórios":
        sub_relatorio = st.sidebar.radio("📊 Relatórios disponíveis",
                                         ["Relatório Analítico", "Relatório Sintético"])
        set_background_static("c:\\projetos\\static\\tela_fundo_azul.png")
        if sub_relatorio == "Relatório Analítico":
            Relatorio.rel_analitico()
        else:
            Relatorio.rel_sintetico()
    elif menu == "Cadastro de Usuário":
        usuarios.cadastrar_usuario()
    elif menu == "Sair":
        st.session_state.clear()
        st.success("✅ Logout realizado com sucesso!")
        st.stop()

main_app()
