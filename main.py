import os
import sys
import warnings
import base64
import streamlit as st

# Adiciona a pasta modules ao path
modules_dir = os.path.join(os.path.dirname(__file__), "modules")
if modules_dir not in sys.path:
    sys.path.append(modules_dir)

warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Agora as importações funcionam
try:
    import financeiro
    import clientes
    import fornecedores
    import planos
    import Relatorio
    import usuarios
    print("✅ Todos os módulos importados com sucesso!")
except ImportError as e:
    print(f"❌ Erro na importação: {e}")
    st.error(f"Erro ao importar módulos: {e}")

st.set_page_config(page_title="Sistema Financeiro", page_icon="💰", layout="wide")

def resource_path(relative_path):
    """Retorna caminho absoluto para recursos"""
    base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def set_login_background(filename="Fundo.png"):
    """Define imagem de fundo do login"""
    path = resource_path(filename)
    print(f"🔍 Buscando: {path}")
    
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
        print("✅ Fundo aplicado com sucesso!")
    else:
        print("⚠️ Usando fundo padrão - arquivo não encontrado")
        # Fundo colorido padrão
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        </style>
        """, unsafe_allow_html=True)

def main_app():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.authenticated:
        set_login_background()
        usuarios.login_screen()
        return

    # Resto do código do menu...
    st.sidebar.title(f"💰 Menu - {st.session_state.user}")
    menu = st.sidebar.radio(
        "Navegação",
        ["Financeiro", "Clientes", "Fornecedores", "Planos", "Relatórios", "Sair"]
    )

    if menu == "Financeiro":
        financeiro.exibir_financeiro()
    elif menu == "Clientes":
        clientes.exibir_clientes()
    elif menu == "Fornecedores":
        fornecedores.exibir_fornecedores()
    elif menu == "Planos":
        planos.exibir_conta_planos()
    elif menu == "Relatórios":
        Relatorio.rel_analitico()
    elif menu == "Sair":
        st.session_state.clear()
        st.success("👋 Logout realizado!")
        st.stop()

if __name__ == "__main__":
    main_app()