# usuarios.py
import streamlit as st
import sqlite3
import hashlib
import os
import sys
from config import DB_FILE

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            )
        """)
        
        # Verificar se o Nilton já existe
        cursor.execute("SELECT * FROM usuarios WHERE usuario = 'Nilton'")
        admin_existente = cursor.fetchone()
        
        if not admin_existente:
            # Criar usuário Nilton como admin
            senha_hash = hashlib.sha256("1502".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO usuarios (usuario, senha, role) VALUES (?, ?, ?)",
                ("Nilton", senha_hash, "admin")
            )
            print("✅ Usuário Nilton criado como admin!")
        else:
            # Garantir que o Nilton seja admin
            if admin_existente['role'] != 'admin':
                cursor.execute("UPDATE usuarios SET role = 'admin' WHERE usuario = 'Nilton'")
                print("✅ Role do Nilton atualizado para admin!")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
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
    if st.session_state.get("role") != "admin":
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
# Interface de login
# ----------------------------
def login_screen():
    """Tela de login do sistema - APENAS LOGIN"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="SFH-01.png" 
                     width="120" 
                     style="margin-bottom: 15px; border-radius: 10px;">
                <h2 style="color: #171ae0; margin-bottom: 5px;">
                    Sistema Financeiro Hórus
                </h2>
                <p style="color: #666; font-size: 18px;">
                    Faça login para acessar o sistema
                </p>
            </div>
        """, unsafe_allow_html=True)

    criar_tabela_usuarios()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔑 Login")
        
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="login_user")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha", key="login_pass")

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

        st.markdown("---")
        st.info("""
        **ℹ️ Informações:**
        - Para cadastrar novos usuários, faça login como **administrador**
        - Acesse o menu **"Cadastro de Usuário"** após o login
        """)

# ----------------------------
# Interface administrativa
# ----------------------------
def interface_cadastro_usuario():
    """Interface de cadastro de usuários (apenas admin)"""
    st.header("👥 Cadastro de Usuários")
    
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
                    st.rerun()

def menu_cadastro_usuario():
    """Função principal para exibir menu de cadastro no Streamlit"""
    
    # ✅ VERIFICAÇÃO DE ADMIN
    if st.session_state.get("role") != "admin":
        st.warning("⚠️ Apenas administradores podem acessar esta funcionalidade.")
        return
    
    # ✅ CHAMA A INTERFACE DE CADASTRO
    interface_cadastro_usuario()
    
    # ✅ MOSTRA A LISTA DE USUÁRIOS
    st.subheader("📋 Usuários Cadastrados")
    usuarios = listar_usuarios()
    
    if usuarios:
        for user in usuarios:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"👤 **{user['usuario']}**")
            with col2:
                st.write(f"Perfil: {user['role']}")
            with col3:
                if user['usuario'] != 'Nilton':  # Não permitir excluir o Nilton
                    if st.button("🗑️", key=f"del_{user['id']}"):
                        st.warning("Funcionalidade de exclusão em desenvolvimento")
    else:
        st.info("ℹ️ Nenhum usuário cadastrado.")