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

# ✅ CORREÇÃO CRÍTICA: CONFIGURAÇÃO DE CAMINHOS PARA NUVEM
base_path = os.path.dirname(__file__)
modulos_path = os.path.join(base_path, "modulos")

# Adiciona múltiplos caminhos possíveis
paths_to_add = [
    base_path,
    modulos_path,
    os.path.join(base_path, "pages"),
    os.path.join(base_path, "utils")
]

for path in paths_to_add:
    if path not in sys.path and os.path.exists(path):
        sys.path.append(path)
        print(f"[INFO] Added to path: {path}")

print(f"[DEBUG] sys.path: {sys.path}")
print(f"[DEBUG] Current directory: {os.getcwd()}")
print(f"[DEBUG] Directory contents: {os.listdir('.')}")

warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# ✅ IMPORT COM TRATAMENTO DE ERRO MELHORADO
MODULES_LOADED = False
loaded_modules = {}

try:
    # Tenta importar de diferentes locais
    try:
        from modulos import financeiro, planos, relatorio, usuarios, relacionamento
        MODULES_LOADED = True
        loaded_modules = {
            'financeiro': financeiro,
            'planos': planos,
            'relatorio': relatorio,
            'usuarios': usuarios,
            'relacionamento': relacionamento
        }
        print("[SUCCESS] Módulos importados via pacote modulos")
        
    except ImportError as e:
        print(f"[TRY 1] Falha no import do pacote: {e}")
        
        # ✅ Tenta importar módulos individualmente
        module_files = [
            'financeiro.py', 
            'planos.py', 
            'relatorio.py', 
            'usuarios.py', 
            'relacionamento.py'
        ]
        
        for module_file in module_files:
            module_name = module_file.replace('.py', '')
            module_paths = [
                os.path.join('modulos', module_file),
                module_file,
                os.path.join(base_path, 'modulos', module_file)
            ]
            
            for module_path in module_paths:
                if os.path.exists(module_path):
                    try:
                        # Importação dinâmica
                        spec = importlib.util.spec_from_file_location(module_name, module_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        loaded_modules[module_name] = module
                        MODULES_LOADED = True
                        print(f"[SUCCESS] Módulo {module_name} carregado de: {module_path}")
                        break
                    except Exception as module_error:
                        print(f"[ERROR] Falha ao carregar {module_path}: {module_error}")
                        continue

except Exception as e:
    MODULES_LOADED = False
    print(f"[CRITICAL] Todos os métodos de import falharam: {e}")

print(f"[STATUS] MODULES_LOADED: {MODULES_LOADED}")
print(f"[STATUS] Módulos carregados: {list(loaded_modules.keys())}")

# ✅ FUNÇÃO DE CAMINHO COMPATÍVEL COM NUVEM
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    full_path = os.path.join(base_path, relative_path)
    
    # Verifica se o arquivo existe
    if not os.path.exists(full_path):
        print(f"[WARNING] Arquivo não encontrado: {full_path}")
        # Tenta encontrar em subdiretórios
        for root, dirs, files in os.walk(base_path):
            if relative_path in files:
                alternative_path = os.path.join(root, relative_path)
                print(f"[INFO] Arquivo encontrado em: {alternative_path}")
                return alternative_path
    
    return full_path

# ✅ SISTEMA DE LOG MELHORADO
def setup_logging():
    """Configura sistema de logging seguro"""
    try:
        log_file = resource_path("app_log.txt")
        import logging
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    except Exception as e:
        print(f"Erro ao configurar logging: {e}")
        return None

logger = setup_logging()

# ✅ SISTEMA DE SESSÃO SEGURA (MANTIDO)
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
    safe_keys = {
        '_streamlit_version', '_runtime', 'Init', 
        'session_initialized', 'SafeState', 'FormSubmitter:login_screen-'
    }
    
    keys_to_remove = []
    for key in list(st.session_state.keys()):
        if key not in safe_keys:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        try:
            del st.session_state[key]
        except Exception:
            pass
    
    initialize_safe_session()

# ✅ BACKGROUNDS SEGUROS - CORREÇÃO PARA NUVEM
def set_login_background(filename="Fundo.png"):
    """Background para tela de login com fallback robusto"""
    try:
        # Lista de possíveis locais
        possible_locations = [
            filename,
            f"modulos/{filename}",
            f"static/{filename}",
            f"assets/{filename}",
            f"images/{filename}",
            resource_path(filename),
            resource_path(f"modulos/{filename}"),
        ]
        
        background_image = None
        for location in possible_locations:
            if os.path.exists(location):
                try:
                    with open(location, "rb") as f:
                        background_image = base64.b64encode(f.read()).decode()
                    print(f"[SUCCESS] Background carregado: {location}")
                    break
                except Exception as e:
                    print(f"[ERROR] Erro ao ler {location}: {e}")
                    continue
        
        if background_image:
            st.markdown(f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{background_image}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                background-repeat: no-repeat;
            }}
            </style>
            """, unsafe_allow_html=True)
        else:
            # Fallback para gradiente
            st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                background-attachment: fixed;
            }
            </style>
            """, unsafe_allow_html=True)
            print("[INFO] Usando background fallback (gradiente)")
            
    except Exception as e:
        print(f"[ERROR] Falha no background: {e}")
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        </style>
        """, unsafe_allow_html=True)

def set_app_background(background_file="tela_fundo_azul.png"):
    """Background para aplicação principal"""
    set_login_background(background_file)  # Reutiliza a mesma lógica

# ✅ COMPONENTES SEGUROS (MANTIDOS)
def safe_radio(label, options, key_suffix):
    import hashlib
    key_hash = hashlib.md5(f"{label}_{str(options)}".encode()).hexdigest()[:8]
    return st.sidebar.radio(
        label,
        options,
        key=f"safe_radio_{key_suffix}_{key_hash}"
    )

def safe_button(label, key_suffix, **kwargs):
    import hashlib
    key_hash = hashlib.md5(f"{label}_{key_suffix}".encode()).hexdigest()[:8]
    return st.button(
        label,
        key=f"safe_btn_{key_suffix}_{key_hash}",
        **kwargs
    )

# ✅ TELA DE LOGIN COM FALLBACK
def safe_login_screen():
    """Tela de login com fallback se módulos não carregarem"""
    try:
        if MODULES_LOADED and 'usuarios' in loaded_modules:
            loaded_modules['usuarios'].login_screen()
        else:
            # ✅ FALLBACK: Tela de login básica
            st.markdown("""
            <div style='text-align: center; padding: 50px 0;'>
                <h1 style='color: white;'>📊 Sistema Financeiro</h1>
                <p style='color: white;'>Entre com suas credenciais</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    with st.form("login_fallback"):
                        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
                        password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
                        submit = st.form_submit_button("🚪 Entrar")
                        
                        if submit:
                            if username and password:
                                # Login básico - ajuste conforme sua lógica
                                st.session_state.authenticated = True
                                st.session_state.user = username
                                st.success("✅ Login realizado com sucesso!")
                                st.rerun()
                            else:
                                st.error("❌ Preencha todos os campos")
            
            st.warning("⚠️ Módulos principais não carregados. Usando modo de emergência.")
            if safe_button("🔄 Tentar Carregar Módulos Novamente", "reload_modules"):
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Erro crítico no login: {e}")
        if safe_button("🔄 Reiniciar Aplicação", "emergency_restart"):
            safe_session_clear()
            st.rerun()

# ✅ EXECUÇÃO DE MÓDULOS COM FALLBACK
def safe_module_execution(module_name, function_name=None):
    """Executa módulos com fallback seguro"""
    try:
        if MODULES_LOADED and module_name in loaded_modules:
            module = loaded_modules[module_name]
            
            # Chama a função principal do módulo
            if function_name and hasattr(module, function_name):
                getattr(module, function_name)()
            elif hasattr(module, f'exibir_{module_name}'):
                getattr(module, f'exibir_{module_name}')()
            elif hasattr(module, module_name):
                getattr(module, module_name)()
            else:
                # Tenta encontrar qualquer função principal
                available_functions = [f for f in dir(module) if not f.startswith('_')]
                if available_functions:
                    getattr(module, available_functions[0])()
                else:
                    st.info(f"📁 Módulo {module_name} carregado, mas nenhuma função encontrada.")
        else:
            st.error(f"❌ Módulo {module_name} não disponível")
            st.info("""
            **Soluções possíveis:**
            - Recarregue a página
            - Verifique se os arquivos do módulo existem
            - Contacte o suporte técnico
            """)
            
    except Exception as e:
        st.error(f"❌ Erro no módulo {module_name}: {str(e)}")
        
        col1, col2 = st.columns(2)
        with col1:
            if safe_button(f"🔄 Recarregar {module_name}", f"reload_{module_name}"):
                st.rerun()
        with col2:
            if safe_button("🏠 Voltar ao Menu", f"menu_{module_name}"):
                st.session_state.authenticated = True
                st.rerun()

# ✅ APLICAÇÃO PRINCIPAL CORRIGIDA
def main_app():
    initialize_safe_session()

    # Tela de login
    if not st.session_state.authenticated:
        set_login_background()
        safe_login_screen()
        return

    # Sidebar
    try:
        with st.sidebar:
            st.markdown(f"""
            <div style='background-color: #2c3e50; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                <h3 style='color: white; margin: 0;'>📊 Sistema Financeiro</h3>
                <p style='color: #ecf0f1; margin: 5px 0 0 0; font-size: 14px;'>
                    Usuário: <strong>{st.session_state.get('user', 'N/A')}</strong>
                </p>
                <p style='color: #bdc3c7; margin: 5px 0 0 0; font-size: 12px;'>
                    Módulos: <strong>{'✅ Carregados' if MODULES_LOADED else '❌ Parcial'}</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            menu_options = ["Financeiro", "Relacionamento", "Planos", "Relatórios", "Cadastro de Usuário", "Sair"]
            menu = safe_radio("Navegação", menu_options, "main_navigation")
            
    except Exception as e:
        st.sidebar.error("❌ Erro na sidebar")
        menu = "Financeiro"

    # Navegação principal
    try:
        set_app_background("tela_fundo_azul.png")
        
        if menu == "Financeiro":
            safe_module_execution("financeiro", "exibir_financeiro")
        elif menu == "Relacionamento":
            safe_module_execution("relacionamento", "formulario_relacionamento")
        elif menu == "Planos":
            safe_module_execution("planos", "exibir_conta_planos")
        elif menu == "Relatórios":
            safe_module_execution("relatorio", "rel_analitico")
        elif menu == "Cadastro de Usuário":
            safe_module_execution("usuarios", "cadastrar_usuario")
        elif menu == "Sair":
            st.header("👋 Encerrar Sessão")
            if safe_button("✅ Confirmar Logout", "confirm_logout"):
                safe_session_clear()
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Erro de navegação: {e}")
        if safe_button("🔄 Reiniciar Navegação", "nav_restart"):
            st.rerun()

# ✅ EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    try:
        main_app()
    except Exception as e:
        st.error(f"❌ Erro crítico na aplicação: {e}")
        if safe_button("🔄 Reiniciar Aplicação Completa", "full_restart"):
            safe_session_clear()
            st.rerun()