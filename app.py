import os
import sys
import warnings
import base64
import streamlit as st

# ✅ CONFIGURAÇÃO ANTECIPADA CRÍTICA
st.set_page_config(
    page_title="Sistema Financeiro NPS",
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Garante que os submódulos sejam encontrados
base_path = os.path.dirname(__file__)
if base_path not in sys.path:
    sys.path.append(base_path)

warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# ✅ IMPORT COM TRATAMENTO DE ERRO ROBUSTO
MODULES_LOADED = False
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

# ✅ SISTEMA DE SESSÃO SEGURA CONTRA removeChild
def initialize_safe_session():
    """Inicialização segura da sessão"""
    required_keys = {
        'authenticated': False,
        'user': None,
        'user_role': 'user',
        'session_initialized': True,
        'SafeState': 'active'
    }
    
    for key, default_value in required_keys.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def safe_session_clear():
    """Limpeza segura que evita o erro removeChild"""
    # Mantém apenas as chaves essenciais do Streamlit
    safe_keys = {
        '_streamlit_version', '_runtime', 'Init', 
        'session_initialized', 'SafeState', 'FormSubmitter:login_screen-'
    }
    
    # Remove apenas chaves problemáticas de forma segura
    keys_to_remove = []
    for key in list(st.session_state.keys()):
        if key not in safe_keys:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        try:
            del st.session_state[key]
        except Exception:
            pass  # Ignora erros na remoção
    
    # Re-inicializa estado seguro
    initialize_safe_session()

# ✅ BACKGROUNDS SEGUROS (MANTIDOS OS PNGs)
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

# ✅ COMPONENTES SEGUROS COM KEYS ÚNICAS
def safe_radio(label, options, key_suffix):
    """Radio button seguro com key única e estável"""
    import hashlib
    key_hash = hashlib.md5(f"{label}_{str(options)}".encode()).hexdigest()[:8]
    return st.sidebar.radio(
        label,
        options,
        key=f"safe_radio_{key_suffix}_{key_hash}"
    )

def safe_button(label, key_suffix, **kwargs):
    """Botão seguro com key única e estável"""
    import hashlib
    key_hash = hashlib.md5(f"{label}_{key_suffix}".encode()).hexdigest()[:8]
    return st.button(
        label,
        key=f"safe_btn_{key_suffix}_{key_hash}",
        **kwargs
    )

def safe_login_screen():
    """Tela de login com tratamento de erro"""
    try:
        if MODULES_LOADED:
            usuarios.login_screen()
        else:
            st.error("⚠️ Módulos não carregados. Recarregue a página.")
            if safe_button("🔄 Recarregar", "login_reload"):
                st.rerun()
    except Exception as e:
        st.error(f"❌ Erro no login: {e}")
        if safe_button("🔄 Tentar Novamente", "login_retry"):
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
        
        # Botões de recuperação com keys seguras
        col1, col2 = st.columns(2)
        with col1:
            if safe_button(f"🔄 Recarregar {module_name}", f"reload_{module_name}"):
                st.rerun()
        with col2:
            if safe_button("🏠 Voltar ao Menu", f"menu_{module_name}"):
                safe_session_clear()
                st.session_state.authenticated = True
                st.rerun()

def main_app():
    # ✅ INICIALIZAÇÃO SEGURA DA SESSÃO
    initialize_safe_session()

    # Tela de login
    if not st.session_state.authenticated:
        set_login_background()
        safe_login_screen()
        return

    # ✅ SIDEBAR COM TRATAMENTO DE ERRO ROBUSTO
    try:
        with st.sidebar:
            st.markdown(f"""
            <div style='background-color: #2c3e50; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                <h3 style='color: white; margin: 0;'>📊 Sistema Financeiro</h3>
                <p style='color: #ecf0f1; margin: 5px 0 0 0; font-size: 14px;'>
                    Usuário: <strong>{st.session_state.get('user', 'N/A')}</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Menu principal com keys seguras
            menu_options = ["Financeiro", "Relacionamento", "Planos", "Relatórios", "Cadastro de Usuário", "Sair"]
            menu = safe_radio("Navegação", menu_options, "main_navigation")
            
            st.markdown("---")
            
            # Botão de recuperação seguro
            if safe_button("🔄 Recarregar Seguro", "safe_reload", help="Recarrega sem erros"):
                safe_session_clear()
                st.rerun()
                
    except Exception as e:
        st.sidebar.error("❌ Erro na sidebar")
        if safe_button("🔄 Recarregar Sidebar", "sidebar_reload"):
            st.rerun()
        menu = "Financeiro"  # Fallback seguro

    # ✅ NAVEGAÇÃO SEGURA COM PROTECÇÃO COMPLETA
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
                sub_options = ["Relatório Analítico", "Relatório Sintético"]
                sub_relatorio = safe_radio("📊 Relatórios disponíveis", sub_options, "sub_reports")
                
                if sub_relatorio == "Relatório Analítico":
                    safe_module_execution(relatorio.rel_analitico, "Relatório Analítico")
                else:
                    safe_module_execution(relatorio.rel_sintetico, "Relatório Sintético")
                    
            except Exception as e:
                st.error(f"❌ Erro no submenu de relatórios: {e}")
                if safe_button("🔄 Recarregar Relatórios", "reload_reports"):
                    st.rerun()
            
        elif menu == "Cadastro de Usuário":
            set_app_background("tela_fundo_azul.png")
            safe_module_execution(usuarios.cadastrar_usuario, "Cadastro de Usuário")
            
        elif menu == "Sair":
            # ✅ LOGOUT SEGURO
            st.header("👋 Encerrar Sessão")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.info("Tem certeza que deseja sair do sistema?")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if safe_button("✅ Sim, sair", "confirm_logout", type="primary", use_container_width=True):
                        safe_session_clear()
                        st.success("✅ Logout realizado com sucesso!")
                        st.rerun()
                
                with col_btn2:
                    if safe_button("❌ Cancelar", "cancel_logout", use_container_width=True):
                        st.rerun()
    
    except Exception as e:
        # ✅ TRATAMENTO GLOBAL DE ERROS ROBUSTO
        st.error(f"❌ Erro inesperado: {str(e)}")
        
        st.markdown("""
        <div style='background-color: #ffebee; padding: 20px; border-radius: 10px; margin: 20px 0;'>
            <h4 style='color: #c62828;'>⚠️ Erro de Renderização</h4>
            <p>O aplicativo encontrou um erro. Tente uma das opções abaixo:</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if safe_button("🔄 Recarregar Página", "soft_reload", use_container_width=True):
                st.rerun()
        with col2:
            if safe_button("🗑️ Limpar Sessão", "clear_session", use_container_width=True):
                safe_session_clear()
                st.rerun()
        with col3:
            if safe_button("🏠 Voltar ao Login", "back_to_login", use_container_width=True):
                safe_session_clear()
                st.session_state.authenticated = False
                st.rerun()

# ✅ EXECUÇÃO PRINCIPAL COM PROTEÇÃO MÁXIMA
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
        
        if safe_button("🔄 Tentar Novamente", "emergency_retry", type="primary"):
            st.rerun()