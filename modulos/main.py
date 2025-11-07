import os
import sys
import warnings
import base64
import streamlit as st

# ======================================================
# 🔧 CONFIGURAÇÕES INICIAIS E IMPORTAÇÕES
# ======================================================

# ✅ CORREÇÃO DAS IMPORTAÇÕES - REMOVER "from . import"
# Importações ABSOLUTAS (funcionam em desenvolvimento e executável)
import financeiro
import planos 
import relatorio
import usuarios
import relacionamento
import formatacao

# ✅ CORREÇÃO DO CAMINHO DO BANCO - SEM DEPENDER DE config.py
def get_db_path():
    """Obtém o caminho correto do banco de dados"""
    if getattr(sys, 'frozen', False):
        # Modo EXECUTÁVEL - banco na mesma pasta do .exe
        return os.path.join(os.path.dirname(sys.executable), 'nps_financeiro.db')
    else:
        # Modo DESENVOLVIMENTO - banco na raiz do projeto
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nps_financeiro.db')

# ✅ USAR A FUNÇÃO LOCALMENTE
DB_PATH = get_db_path()

# Configurar o caminho para o executável
if getattr(sys, 'frozen', False):
    # Modo executável - adicionar o diretório dos módulos ao path
    modulos_dir = os.path.join(os.path.dirname(sys.executable), 'modulos')
    if modulos_dir not in sys.path:
        sys.path.insert(0, modulos_dir)

warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

print("[INFO] main.py foi iniciado com sucesso!")
print(f"📁 Caminho do banco: {DB_PATH}")

# ✅ CORREÇÃO: MOVER st.set_page_config PARA FORA DE FUNÇÕES
st.set_page_config(page_title="HORUS - NPS Financeiro", page_icon="📊", layout="wide")

# ======================================================
# 🧩 FUNÇÕES DE SUPORTE
# ======================================================
def styled_subheader(text, font_size="14px", color="#171ae0"):
    """
    Exibe um subtítulo com fonte personalizada
    """
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

def resource_path(relative_path: str) -> str:
    """Retorna o caminho absoluto do recurso, mesmo em ambiente PyInstaller."""
    try:
        # ✅ CORREÇÃO: Usar sys._MEIPASS para modo executável
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(__file__))
    except Exception:
        base_path = os.path.abspath(".")
    
    full_path = os.path.join(base_path, relative_path)
    return full_path

# ✅ CORREÇÃO: REDIRECIONAMENTO DE LOG MELHORADO
def setup_logging():
    """Configura o sistema de logging"""
    log_file = resource_path("erro_log.txt")
    try:
        log = open(log_file, "a", encoding="utf-8")
        sys.stdout = log
        sys.stderr = log
        print("\n--- Nova execução ---")
        print(f"Modo executável: {getattr(sys, 'frozen', False)}")
        print(f"DB_PATH: {DB_PATH}")
        print(f"Diretório atual: {os.getcwd()}")
    except Exception as e:
        print(f"Erro ao configurar log: {e}")

# Configurar logging
setup_logging()

# ======================================================
# 🎨 FUNÇÕES DE BACKGROUND
# ======================================================

def set_login_background(filename="modulos/static/Fundo.png"):
    """Define o fundo da tela de login."""
    # ✅ CORREÇÃO: Usar caminhos relativos
    path = resource_path(filename)
    print(f"📁 Procurando imagem de login em: {path}")
    
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
    else:
        print(f"❌ Imagem de login não encontrada: {path}")

def set_background_static(relative_path="modulos/static/tela_fundo_azul.png"):
    """Define o fundo fixo para telas internas."""
    # ✅ CORREÇÃO: Usar caminhos relativos
    path = resource_path(relative_path)
    print(f"📁 Procurando imagem de fundo em: {path}")
    
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
    else:
        print(f"❌ Imagem de fundo não encontrada: {path}")

# ======================================================
# 🚀 FUNÇÃO PRINCIPAL DA APLICAÇÃO
# ======================================================

def main_app():
    """Função principal que gerencia autenticação e menus."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # Se o usuário não estiver autenticado, exibe a tela de login
    if not st.session_state["authenticated"]:
        set_login_background()
        usuarios.login_screen()
        return

    # Menu lateral
    st.sidebar.markdown(
    f"""
    <div style="font-size: 16px; font-weight: bold; color: #171ae0; margin-bottom: 20px;">
        📌 Menu - Usuário: {st.session_state['user']}
    </div>
    """,
    unsafe_allow_html=True
)
    menu = st.sidebar.radio(
        "Navegação",
        ["Financeiro", "Relacionamento", "Planos",
         "Relatórios", "Cadastro de Usuário", "Sair"]
    )

    # ==================================================
    # 📁 SEÇÕES PRINCIPAIS DO SISTEMA
    # ==================================================

    if menu == "Financeiro":
        set_background_static()
        financeiro.exibir_financeiro()

    elif menu == "Relacionamento":
        set_background_static()
        relacionamento.show()

    elif menu == "Planos":
        set_background_static()
        planos.exibir_conta_planos()

    elif menu == "Relatórios":
        set_background_static()
        sub_relatorio = st.sidebar.radio(
            "📊 Relatórios disponíveis",
            [
                "Movimento Caixa e Banco",
                "Relatório por Categoria",
                "Relatório Analítico", 
                "Relatório Sintético", 
                "Relação Analítico", 
                "Relação Sintético"               
            ]
        )

        if sub_relatorio == "Movimento Caixa e Banco":
            relatorio.mov_caixa_banco()
        elif sub_relatorio == "Relatório por Categoria":
            relatorio.relatorio_categoria()
        elif sub_relatorio == "Relatório Analítico":
            relatorio.rel_analitico()
        elif sub_relatorio == "Relatório Sintético":
            relatorio.rel_sintetico()
        elif sub_relatorio == "Relação Analítico":
            relatorio.relacao_analitico()
        elif sub_relatorio == "Relação Sintético":
            relatorio.relacao_sintetico()

    elif menu == "Cadastro de Usuário":
        set_background_static()
        usuarios.menu_cadastro_usuario()

    elif menu == "Sair":
        st.session_state.clear()
        st.success("✅ Logout realizado com sucesso!")
        st.stop()

# ======================================================
# ▶️ EXECUÇÃO PRINCIPAL
# ======================================================

if __name__ == "__main__":
    main_app()