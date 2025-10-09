import streamlit as st
import sqlite3
import hashlib

DB_FILE = "financeiro.db"

# ----------------------------
# Funções de banco de dados
# ----------------------------
def conectar_db():
    """Conecta ao banco de dados"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"❌ Erro ao conectar com banco: {e}")
        return None

def criar_tabela_usuarios():
    """Cria a tabela de usuários se não existir"""
    conn = conectar_db()
    if conn is None:
        return False
        
    cursor = conn.cursor()
    try:
        # CORREÇÃO: Tabela com estrutura simplificada
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            )
        """)
        
        # CORREÇÃO: Verificar se o admin já existe ANTES de inserir
        cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
        admin_existente = cursor.fetchone()
        
        if not admin_existente:
            senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO usuarios (usuario, senha, role) VALUES (?, ?, ?)",
                ("admin", senha_hash, "admin")
            )
            print("✅ Usuário admin criado com sucesso!")
        else:
            print("ℹ️ Usuário admin já existe")
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Erro SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False
    finally:
        conn.close()

def autenticar_usuario(usuario, senha):
    """Autentica usuário no sistema"""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    conn = conectar_db()
    if conn is None:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", 
            (usuario, senha_hash)
        )
        user = cursor.fetchone()
        return user is not None
    except Exception as e:
        print(f"❌ Erro na autenticação: {e}")
        return False
    finally:
        conn.close()

def cadastrar_usuario(usuario, senha):
    """Cadastra novo usuário"""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    conn = conectar_db()
    if conn is None:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", 
            (usuario, senha_hash)
        )
        conn.commit()
        st.success("✅ Usuário cadastrado com sucesso!")
        return True
    except sqlite3.IntegrityError:
        st.error("❌ Usuário já existe!")
        return False
    except Exception as e:
        st.error(f"❌ Erro ao cadastrar: {e}")
        return False
    finally:
        conn.close()

def obter_role_usuario(usuario):
    """Obtém o role (perfil) do usuário"""
    conn = conectar_db()
    if conn is None:
        return "user"
        
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM usuarios WHERE usuario = ?", (usuario,))
        result = cursor.fetchone()
        return result["role"] if result else "user"
    except Exception as e:
        print(f"❌ Erro ao obter role: {e}")
        return "user"
    finally:
        conn.close()

# ----------------------------
# Tela de login
# ----------------------------
def login_screen():
    """Tela de login do sistema"""
    st.markdown("""
        <h2 style="text-align: center; margin-bottom: 20px;">
            💰 Sistema Financeiro
        </h2>
    """, unsafe_allow_html=True)

    # CORREÇÃO: Criar tabela com tratamento de erro
    try:
        criar_tabela_usuarios()
        print("✅ Tabela de usuários verificada/criada")
    except Exception as e:
        st.error(f"❌ Erro ao configurar banco: {e}")
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown("""
                <div style="
                    padding: 25px; 
                    border-radius: 12px; 
                    background-color: #f9f9f9; 
                    box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
            """, unsafe_allow_html=True)

            menu = ["Login", "Cadastrar"]
            escolha = st.radio("🔑 Escolha uma opção", menu, horizontal=True)

            if escolha == "Login":
                usuario = st.text_input("Usuário", value="admin", key="login_user")
                senha = st.text_input("Senha", type="password", value="admin123", key="login_pass")

                if st.button("Entrar", use_container_width=True):
                    if not usuario or not senha:
                        st.error("❌ Preencha todos os campos!")
                    elif autenticar_usuario(usuario, senha):
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = usuario
                        st.session_state["role"] = obter_role_usuario(usuario)
                        st.success(f"✅ Bem-vindo, {usuario}!")
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos!")

            elif escolha == "Cadastrar":
                new_username = st.text_input("Novo usuário", key="cad_user")
                new_senha = st.text_input("Nova senha", type="password", key="cad_pass")
                confirm_senha = st.text_input("Confirme a senha", type="password", key="cad_conf")

                if st.button("Cadastrar", use_container_width=True):
                    if not new_username or not new_senha:
                        st.warning("⚠️ Preencha todos os campos!")
                    elif new_senha != confirm_senha:
                        st.error("❌ As senhas não coincidem!")
                    else:
                        if cadastrar_usuario(new_username, new_senha):
                            st.success("✅ Usuário cadastrado com sucesso! Faça login.")

            st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Gestão de usuários (para admin)
# ----------------------------
def interface_cadastro_usuario():
    """Interface de cadastro de usuários (apenas admin)"""
    st.header("👥 Cadastro de Usuários")
    
    # Verificar se é admin
    if st.session_state.get("user") != "admin":
        st.warning("⚠️ Apenas administradores podem cadastrar usuários.")
        return

    with st.form("form_cadastro_usuario"):
        usuario = st.text_input("Novo usuário")
        senha = st.text_input("Senha", type="password")
        confirm_senha = st.text_input("Confirmar senha", type="password")
        role = st.selectbox("Perfil", ["user", "admin"])
        
        if st.form_submit_button("Cadastrar Usuário"):
            if not usuario or not senha:
                st.error("❌ Preencha todos os campos!")
            elif senha != confirm_senha:
                st.error("❌ As senhas não coincidem!")
            else:
                if cadastrar_usuario_admin(usuario, senha, role):
                    st.success(f"✅ Usuário {usuario} cadastrado com sucesso!")

def cadastrar_usuario_admin(usuario, senha, role="user"):
    """Cadastra usuário com role específico (apenas para admin)"""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    conn = conectar_db()
    if conn is None:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (usuario, senha, role) VALUES (?, ?, ?)", 
            (usuario, senha_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("❌ Usuário já existe!")
        return False
    except Exception as e:
        st.error(f"❌ Erro ao cadastrar: {e}")
        return False
    finally:
        conn.close()

def listar_usuarios():
    """Lista todos os usuários (apenas admin)"""
    if st.session_state.get("user") != "admin":
        return []
        
    conn = conectar_db()
    if conn is None:
        return []
        
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, usuario, role FROM usuarios ORDER BY usuario")
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")
        return []
    finally:
        conn.close()

# ----------------------------
# Função principal de cadastro (para uso no menu)
# ----------------------------
def cadastrar_usuario():
    """Função principal para cadastro de usuários no menu"""
    interface_cadastro_usuario()
    
    # Mostrar lista de usuários se for admin
    if st.session_state.get("user") == "admin":
        st.subheader("📋 Usuários Cadastrados")
        usuarios = listar_usuarios()
        if usuarios:
            for user in usuarios:
                st.write(f"👤 **{user['usuario']}** - Perfil: {user['role']}")
        else:
            st.info("ℹ️ Nenhum usuário cadastrado.")