import streamlit as st
import sqlite3
import base64
import os

DB_FILE = "financeiro.db"


def set_login_background_planos(filename="tela_fundo_azul.png"):
    """
    Aplica uma imagem de fundo no Streamlit.
    Procura o arquivo na pasta 'static/' dentro da raiz do projeto.
    """

    # Descobre onde está o main.py
    try:
        import __main__
        main_file = os.path.abspath(__main__.__file__)
    except:
        main_file = os.path.abspath(__file__)

    project_root = os.path.dirname(main_file)

    # Caminho da pasta static
    static_dir = os.path.join(project_root, "")
    image_path = os.path.join(static_dir, filename)

    if not os.path.exists(image_path):
        st.error(
            f"❌ Arquivo não encontrado: {filename}\n"
            f"Tentado em:\n- {image_path}\n"
            f"(project_root detectado: {project_root})"
        )
        return

    # Lê e converte para base64
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ----------------------------
# Conexão com o banco de dados
# ----------------------------
def conectar_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------
# Criação da tabela de Plano
# ----------------------------
def criar_tabela_planos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Plano (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Grupo TEXT,
            Subgrupo TEXT,
            Plano TEXT,
            Classificacao TEXT
        )
    """)
    conn.commit()
    conn.close()

# ----------------------------
# Inserir plano
# ----------------------------
def inserir_plano(grupo, subgrupo, plano, classificacao):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Plano (Grupo, Subgrupo, Plano, Classificacao) VALUES (?, ?, ?, ?)",
        (grupo, subgrupo, plano, classificacao)
    )
    conn.commit()
    conn.close()

# ----------------------------
# Atualizar plano
# ----------------------------
def atualizar_plano(id, grupo, subgrupo, plano, classificacao):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Plano SET Grupo=?, Subgrupo=?, Plano=?, Classificacao=? WHERE id=?",
        (grupo, subgrupo, plano, classificacao, id)
    )
    conn.commit()
    conn.close()

# ----------------------------
# Listar planos
# ----------------------------
def listar_planos():
   conn = conectar_db()
   cursor = conn.cursor()
   cursor.execute("SELECT * FROM Plano ORDER BY Grupo, Subgrupo, Plano, Classificacao")
   resultados = cursor.fetchall()
   conn.close()
   return resultados

# ----------------------------
# Excluir plano
# ----------------------------
def excluir_plano(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Plano WHERE id=?", (id,))
    conn.commit()
    conn.close()

# ----------------------------
# Função auxiliar para acessar colunas de forma segura
# ----------------------------
def obter_valor_plano(plano, coluna):
    """Obtém valor de coluna de forma segura para sqlite3.Row"""
    try:
        # Tenta acessar a coluna diretamente
        return plano[coluna]
    except (KeyError, IndexError):
        try:
            # Tenta acessar com letras minúsculas
            return plano[coluna.lower()]
        except (KeyError, IndexError):
            try:
                # Tenta acessar com letras maiúsculas
                return plano[coluna.upper()]
            except (KeyError, IndexError):
                return None

# ----------------------------
# Exibir no Streamlit
# ----------------------------
def exibir_conta_planos():
    criar_tabela_planos()
    st.title("📋 Cadastro de Planos")

    planos_list = listar_planos()

    # Selectbox para escolher um plano existente (para alterar)
    plano_selecionado = None
    if planos_list:
        plano_opcoes = {}
        for p in planos_list:
            # CORREÇÃO: Usar função auxiliar para acessar colunas
            grupo = obter_valor_plano(p, 'Grupo') or ''
            subgrupo = obter_valor_plano(p, 'Subgrupo') or ''
            plano_nome = obter_valor_plano(p, 'Plano') or ''
            plano_id = obter_valor_plano(p, 'id') or ''
            
            chave = f"{plano_id} - {grupo} / {subgrupo} / {plano_nome}"
            plano_opcoes[chave] = p

        escolha = st.selectbox("Selecione um plano para alterar (ou deixe em branco para novo):", [""] + list(plano_opcoes.keys()))
        if escolha and escolha in plano_opcoes:
            plano_selecionado = plano_opcoes[escolha]

    # Se o usuário escolheu um plano, preenche o formulário com os dados
    with st.form("form_plano"):
        # CORREÇÃO: Usar função auxiliar para obter valores
        grupo_valor = obter_valor_plano(plano_selecionado, 'Grupo') if plano_selecionado else ""
        subgrupo_valor = obter_valor_plano(plano_selecionado, 'Subgrupo') if plano_selecionado else ""
        plano_valor = obter_valor_plano(plano_selecionado, 'Plano') if plano_selecionado else ""
        classificacao_valor = obter_valor_plano(plano_selecionado, 'Classificacao') if plano_selecionado else ""

        grupo = st.text_input("Grupo", value=grupo_valor)
        subgrupo = st.text_input("Subgrupo", value=subgrupo_valor)
        plano = st.text_input("Plano", value=plano_valor)
        classificacao = st.text_input("Classificação", value=classificacao_valor)

        col1, col2 = st.columns(2)
        with col1:
            inserir = st.form_submit_button("➕ Inserir")
        with col2:
            alterar = st.form_submit_button("✏️ Alterar")

        if inserir:
            if grupo and subgrupo and plano and classificacao:
                inserir_plano(grupo, subgrupo, plano, classificacao)
                st.success("✅ Plano inserido com sucesso!")
                st.rerun()
            else:
                st.error("❌ Todos os campos são obrigatórios!")

        if alterar:
            if plano_selecionado:
                if grupo and subgrupo and plano and classificacao:
                    # CORREÇÃO: Obter ID usando função auxiliar
                    plano_id = obter_valor_plano(plano_selecionado, 'id')
                    atualizar_plano(plano_id, grupo, subgrupo, plano, classificacao)
                    st.success("✅ Plano alterado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Todos os campos são obrigatórios!")
            else:
                st.warning("⚠️ Selecione um plano para alterar.")

    # Botão para excluir plano selecionado (fora do formulário)
    if plano_selecionado:
        st.markdown("---")
        st.subheader("🗑️ Excluir Plano")
        
        # CORREÇÃO: Usar função auxiliar para obter valores
        grupo_display = obter_valor_plano(plano_selecionado, 'Grupo') or ''
        subgrupo_display = obter_valor_plano(plano_selecionado, 'Subgrupo') or ''
        plano_display = obter_valor_plano(plano_selecionado, 'Plano') or ''
        
        st.warning(f"Você selecionou: {grupo_display} / {subgrupo_display} / {plano_display}")
        
        if st.button("🗑️ Excluir Plano Selecionado", type="secondary"):
            # CORREÇÃO: Obter ID usando função auxiliar
            plano_id = obter_valor_plano(plano_selecionado, 'id')
            excluir_plano(plano_id)
            st.success("✅ Plano excluído com sucesso!")
            st.rerun()

    # Exibir lista de planos cadastrados
    if planos_list:
        st.markdown("---")
        st.subheader("📋 Planos Cadastrados")
        
        # CORREÇÃO: Usar função auxiliar para acessar colunas
        for plano in planos_list:
            grupo = obter_valor_plano(plano, 'Grupo') or 'Não definido'
            subgrupo = obter_valor_plano(plano, 'Subgrupo') or 'Não definido'
            plano_nome = obter_valor_plano(plano, 'Plano') or 'Não definido'
            classificacao_valor = obter_valor_plano(plano, 'Classificacao') or 'Não definida'
            
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"**Grupo:** {grupo}")
            with col2:
                st.write(f"**Subgrupo:** {subgrupo}")
            with col3:
                st.write(f"**Plano:** {plano_nome}")
            with col4:
                st.write(f"**Classificação:** {classificacao_valor}")
            
            st.markdown("---")

# Para compatibilidade com o main.py
def exibir_planos():
    exibir_conta_planos()

if __name__ == "__main__":
    exibir_conta_planos()