import os
import sys
import warnings
import base64
import streamlit as st

# ✅ CONFIGURAÇÃO ANTECIPADA PARA EVITAR ERROS
st.set_page_config(page_title="Financeiro", page_icon="📊", layout="wide")

# Garante que os submódulos sejam encontrados
base_path = os.path.dirname(__file__)
if base_path not in sys.path:
    sys.path.append(base_path)

warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# ✅ IMPORT COM TRATAMENTO DE ERRO
try:
    from modulos import financeiro
    from modulos import planos
    from modulos import relatorio
    from modulos import usuarios
    from modulos import relacionamento
    MODULES_LOADED = True
    print("[INFO] Módulos importados com sucesso!")
except ImportError as e:
    MODULES_LOADED = False
    print(f"[ERRO] Import falhou: {e}")

def resource_path(relative_path: str) -> str:
    """Função compatível com nuvem"""
    if getattr(sys, "_MEIPASS", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

sys.path.append(resource_path("modulos"))

# ✅ LOG SEGURO
log_file = resource_path("erro_log.txt")
try:
    log = open(log_file, "a", encoding="utf-8")
    sys.stdout = log
    sys.stderr = log
    print("\n--- Nova execução ---")
except Exception as e:
    print(f"Erro ao abrir log: {e}")

def safe_session_clear():
    """Limpeza segura da sessão para evitar erro removeChild"""
    keys_to_keep = ['_streamlit_version', '_runtime', 'FormSubmitter:login_screen-']
    new_state = {}
    
    for key in keys_to_keep:
        if key in st.session_state:
            new_state[key] = st.session_state[key]
    
    # Limpa apenas as chaves problemáticas
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            try:
                del st.session_state[key]
            except:
                pass

def set_login_background(filename="Fundo.png"):
    """Background para tela de login com fallback"""
    try:
        # Tenta vários caminhos possíveis
        possible_paths = [
            resource_path(filename),
            resource_path(f"modulos/{filename}"),
            resource_path(f"static/{filename}"),
            filename  # Caminho direto
        ]
        
        background_set = False
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
                encoded = base64.b64encode(data).decode()
                st.markdown(f"""
                <style>
                .stApp {{
                    background-image: url("data:image/png;base64,{encoded}");
                    background-size: cover;
                    background-attachment: fixed;
                }}
                </style>
                """, unsafe_allow_html=True)
                background_set = True
                print(f"[INFO] Background carregado: {path}")
                break
        
        if not background_set:
            # Fallback para cor sólida
            st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            </style>
            """, unsafe_allow_html=True)
            print("[INFO] Usando background fallback")
            
    except Exception as e:
        print(f"[ERRO] Background não carregado: {e}")
        # Fallback seguro
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        </style>
        """, unsafe_allow_html=True)

def set_app_background(background_file="tela_fundo_azul.png"):
    """Background para aplicação principal"""
    try:
        # Tenta vários caminhos possíveis
        possible_paths = [
            resource_path(background_file),
            resource_path(f"modulos/{background_file}"),
            resource_path(f"modulos/static/{background_file}"),
            resource_path(f"static/{background_file}"),
            background_file  # Caminho direto
        ]
        
        background_set = False
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
                encoded = base64.b64encode(data).decode()
                st.markdown(f"""
                <style>
                .stApp {{
                    background-image: url("data:image/png;base64,{encoded}");
                    background-size: cover;
                    background-attachment: fixed;
                }}
                </style>
                """, unsafe_allow_html=True)
                background_set = True
                print(f"[INFO] App background carregado: {path}")
                break
        
        if not background_set:
            # Fallback para cor sólida
            st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }
            </style>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        print(f"[ERRO] App background não carregado: {e}")
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        </style>
        """, unsafe_allow_html=True)

def safe_login_screen():
    """Tela de login com tratamento de erro"""
    try:
        if MODULES_LOADED:
            usuarios.login_screen()
        else:
            st.error("⚠️ Módulos não carregados. Recarregue a página.")
            if st.button("🔄 Recarregar"):
                st.rerun()
    except Exception as e:
        st.error(f"❌ Erro no login: {e}")
        if st.button("🔄 Tentar Novamente"):
            st.rerun()

def safe_module_execution(module_function, module_name):
    """Executa módulos com tratamento seguro de erro"""
    try:
        if MODULES_LOADED:
            module_function()
        else:
            st.error(f"❌ Módulo {module_name} não disponível")
    except Exception as e:
        st.error(f"❌ Erro no módulo {module_name}: {e}")
        
        # Botões de recuperação
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"🔄 Recarregar {module_name}", key=f"reload_{module_name}"):
                st.rerun()
        with col2:
            if st.button("🏠 Voltar ao Menu", key=f"menu_{module_name}"):
                # Limpa apenas o estado problemático
                if "authenticated" in st.session_state:
                    st.session_state.authenticated = True
                st.rerun()

def main_app():
    # ✅ INICIALIZAÇÃO SEGURA DA SESSÃO
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "menu_initialized" not in st.session_state:
        st.session_state["menu_initialized"] = False

    # Tela de login
    if not st.session_state["authenticated"]:
        set_login_background()
        safe_login_screen()
        return

    # ✅ SIDEBAR COM TRATAMENTO DE ERRO
    try:
        st.sidebar.title(f"📌 Menu - Usuário: {st.session_state['user']}")
        
        # Botão de recuperação na sidebar
        if st.sidebar.button("🔄 Recarregar Seguro", help="Recarrega sem erros"):
            safe_session_clear()
            st.rerun()
        
        st.sidebar.markdown("---")
        
        menu = st.sidebar.radio(
            "Navegação",
            ["Financeiro", "Relacionamento", "Planos",
             "Relatórios", "Cadastro de Usuário", "Sair"],
            key="main_menu_radio"  # ✅ KEY ÚNICA
        )
        
    except Exception as e:
        st.sidebar.error("❌ Erro na sidebar")
        if st.sidebar.button("🔄 Recarregar Sidebar"):
            st.rerun()
        menu = "Financeiro"  # Fallback seguro

    # ✅ NAVEGAÇÃO SEGURA
    try:
        if menu == "Financeiro":
            set_app_background("tela_fundo_azul.png")
            safe_module_execution(financeiro.exibir_financeiro, "Financeiro")
            
        elif menu == "Relacionamento":
            set_app_background("tela_fundo_azul.png")
            safe_module_execution(relacionamento.formulario_relacionamento, "Relacionamento")
            
        elif menu == "Planos":
            set_app_background("tela_fundo_azul.png")
            safe_module_execution(planos.exibir_conta_planos, "Planos")
            
        elif menu == "Relatórios":
            set_app_background("tela_fundo_azul.png")
            
            # ✅ SUBMENU SEGURO
            try:
                sub_relatorio = st.sidebar.radio(
                    "📊 Relatórios disponíveis",
                    ["Relatório Analítico", "Relatório Sintético"],
                    key="submenu_relatorios"
                )
                
                if sub_relatorio == "Relatório Analítico":
                    safe_module_execution(relatorio.rel_analitico, "Relatório Analítico")
                else:
                    safe_module_execution(relatorio.rel_sintetico, "Relatório Sintético")
                    
            except Exception as e:
                st.error(f"❌ Erro no submenu de relatórios: {e}")
                if st.button("🔄 Recarregar Relatórios"):
                    st.rerun()
            
        elif menu == "Cadastro de Usuário":
            set_app_background()
            safe_module_execution(usuarios.cadastrar_usuario, "Cadastro de Usuário")
            
        elif menu == "Sair":
            # ✅ LOGOUT SEGURO
            st.header("👋 Encerrar Sessão")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.info("Tem certeza que deseja sair do sistema?")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Sim, sair", use_container_width=True, type="primary"):
                        safe_session_clear()
                        st.success("✅ Logout realizado com sucesso!")
                        st.rerun()
                
                with col_btn2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.rerun()
    
    except Exception as e:
        # ✅ TRATAMENTO GLOBAL DE ERROS
        st.error(f"❌ Erro inesperado: {str(e)}")
        
        st.markdown("""
        <div style='background-color: #ffebee; padding: 20px; border-radius: 10px; margin: 20px 0;'>
            <h4 style='color: #c62828;'>⚠️ Erro de Renderização</h4>
            <p>O aplicativo encontrou um erro. Tente uma das opções abaixo:</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Recarregar Página", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🗑️ Limpar Sessão", use_container_width=True):
                safe_session_clear()
                st.rerun()
        with col3:
            if st.button("🏠 Voltar ao Login", use_container_width=True):
                safe_session_clear()
                st.session_state.authenticated = False
                st.rerun()

# ✅ EXECUÇÃO PRINCIPAL COM PROTEÇÃO
if __name__ == "__main__":
    try:
        main_app()
    except Exception as e:
        # ✅ FALLBACK DE EMERGÊNCIA
        st.markdown("""
        <div style='text-align: center; padding: 100px; background-color: #fff3e0; 
                 border-radius: 15px; margin: 50px 0;'>
            <h1 style='color: #ef6c00;'>🔧 Sistema em Manutenção</h1>
            <p style='color: #555; font-size: 18px;'>O aplicativo está passando por ajustes técnicos.</p>
            <p style='color: #777;'>Tente recarregar a página ou aguarde alguns instantes.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Tentar Novamente", type="primary"):
            st.rerun()