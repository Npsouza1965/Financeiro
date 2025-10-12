import streamlit as st
import sqlite3
import base64
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "nps_financeiro.db")


def set_login_background_planos(filename="tela_fundo_azul.png"):
    """
    Aplica uma imagem de fundo no Streamlit.
    Procura o arquivo na pasta 'static/' dentro da raiz do projeto.
    """
    try:
        import __main__
        main_file = os.path.abspath(__main__.__file__)
    except:
        main_file = os.path.abspath(__file__)

    project_root = os.path.dirname(main_file)
    static_dir = os.path.join(project_root, "")
    image_path = os.path.join(static_dir, filename)

    if not os.path.exists(image_path):
        st.error(
            f"❌ Arquivo não encontrado: {filename}\n"
            f"Tentado em:\n- {image_path}\n"
            f"(project_root detectado: {project_root})"
        )
        return

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
# Criação da tabela de plano
# ----------------------------
def criar_tabela_planos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plano (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT,
            subgrupo TEXT,
            plano TEXT,
            categoria TEXT
        )
    """)
    conn.commit()
    conn.close()


# ----------------------------
# Inserir plano
# ----------------------------
def inserir_plano(grupo, subgrupo, plano, categoria):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO plano (grupo, subgrupo, plano, categoria) VALUES (?, ?, ?, ?)",
        (grupo, subgrupo, plano, categoria)
    )
    conn.commit()
    conn.close()


# ----------------------------
# Atualizar plano
# ----------------------------
def atualizar_plano(id, grupo, subgrupo, plano, categoria):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE plano SET grupo=?, subgrupo=?, plano=?, categoria=? WHERE id=?",
        (grupo, subgrupo, plano, categoria, id)
    )
    conn.commit()
    conn.close()


# ----------------------------
# Listar planos
# ----------------------------
def listar_planos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plano ORDER BY grupo, subgrupo, plano, categoria")
    resultados = cursor.fetchall()
    conn.close()
    return resultados


# ----------------------------
# Excluir plano
# ----------------------------
def excluir_plano(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plano WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ----------------------------
# Função auxiliar para acessar colunas de forma segura
# ----------------------------
def obter_valor_plano(plano, coluna):
    """Obtém valor de coluna de forma segura para sqlite3.Row"""
    try:
        return plano[coluna]
    except (KeyError, IndexError):
        try:
            return plano[coluna.lower()]
        except (KeyError, IndexError):
            try:
                return plano[coluna.upper()]
            except (KeyError, IndexError):
                return None


# ----------------------------
# Exibir no Streamlit (sem listagem final)
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
            grupo = obter_valor_plano(p, 'grupo') or ''
            subgrupo = obter_valor_plano(p, 'subgrupo') or ''
            plano_nome = obter_valor_plano(p, 'plano') or ''
            plano_id = obter_valor_plano(p, 'id') or ''
            chave = f"{plano_id} - {grupo} / {subgrupo} / {plano_nome}"
            plano_opcoes[chave] = p

        escolha = st.selectbox(
            "Selecione um plano para alterar (ou deixe em branco para novo):",
            [""] + list(plano_opcoes.keys())
        )
        if escolha and escolha in plano_opcoes:
            plano_selecionado = plano_opcoes[escolha]

    # Formulário de cadastro/alteração
    with st.form("form_plano"):
        grupo_valor = obter_valor_plano(plano_selecionado, 'grupo') if plano_selecionado else ""
        subgrupo_valor = obter_valor_plano(plano_selecionado, 'subgrupo') if plano_selecionado else ""
        plano_valor = obter_valor_plano(plano_selecionado, 'plano') if plano_selecionado else ""
        classificacao_valor = obter_valor_plano(plano_selecionado, 'categoria') if plano_selecionado else ""

        grupo = st.text_input("Grupo", value=grupo_valor)
        subgrupo = st.text_input("Subgrupo", value=subgrupo_valor)
        plano = st.text_input("Plano", value=plano_valor)
        categoria = st.text_input("Classificação", value=classificacao_valor)

        col1, col2 = st.columns(2)
        with col1:
            inserir = st.form_submit_button("➕ Inserir")
        with col2:
            alterar = st.form_submit_button("✏️ Alterar")

        if inserir:
            if grupo and subgrupo and plano and categoria:
                inserir_plano(grupo, subgrupo, plano, categoria)
                st.success("✅ Plano inserido com sucesso!")
                st.rerun()
            else:
                st.error("❌ Todos os campos são obrigatórios!")

        if alterar:
            if plano_selecionado:
                if grupo and subgrupo and plano and categoria:
                    plano_id = obter_valor_plano(plano_selecionado, 'id')
                    atualizar_plano(plano_id, grupo, subgrupo, plano, categoria)
                    st.success("✅ Plano alterado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Todos os campos são obrigatórios!")
            else:
                st.warning("⚠️ Selecione um plano para alterar.")

    # Botão de exclusão
    if plano_selecionado:
        st.markdown("---")
        st.subheader("🗑️ Excluir Plano")

        grupo_display = obter_valor_plano(plano_selecionado, 'grupo') or ''
        subgrupo_display = obter_valor_plano(plano_selecionado, 'subgrupo') or ''
        plano_display = obter_valor_plano(plano_selecionado, 'plano') or ''

        st.warning(f"Você selecionou: {grupo_display} / {subgrupo_display} / {plano_display}")

        if st.button("🗑️ Excluir Plano Selecionado", type="secondary"):
            plano_id = obter_valor_plano(plano_selecionado, 'id')
            excluir_plano(plano_id)
            st.success("✅ Plano excluído com sucesso!")
            st.rerun()


if __name__ == "__main__":
    exibir_conta_planos()
