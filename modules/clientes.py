import streamlit as st
import sqlite3
import base64
import os
import warnings
import pandas as pd
from datetime import date

from .formatacao import (
    validar_cpf,
    formatar_cep,
    formatar_telefone,
    formatar_cpf,
    buscar_endereco_por_cep,
)


DB_FILE = "financeiro.db"

# ----------------------------
# Background
# ----------------------------
def set_login_background_clientes(filename="tela_fundo_azul.png"):
    try:
        import __main__
        main_file = os.path.abspath(__main__.__file__)
    except:
        main_file = os.path.abspath(__file__)
    project_root = os.path.dirname(main_file)
    static_dir = os.path.join(project_root, "")
    image_path = os.path.join(static_dir, filename)
    if not os.path.exists(image_path):
        st.error(f"❌ Arquivo não encontrado: {filename}\nTentado em:\n- {image_path}\n(project_root detectado: {project_root})")
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
# Conexão com banco de dados
# ----------------------------
def conectar_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------
# Criação da tabela clientes
# ----------------------------
def criar_tabela_clientes():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Nome TEXT,
            CPF TEXT,
            DataNascimento TEXT,       
            CEP TEXT,
            Endereco TEXT,
            Bairro TEXT,       
            Cidade TEXT,
            UF TEXT,         
            Tipo TEXT,
            Telefone TEXT,
            Observacao TEXT
        )
    """)
    conn.commit()
    conn.close()

# ----------------------------
# Inserir ou atualizar cliente
# ----------------------------
def salvar_cliente_sql(dados):
    conn = conectar_db()
    cursor = conn.cursor()
    if "id" in dados and dados["id"]:
        cursor.execute("""
            UPDATE clientes
            SET Nome=?, CPF=?, DataNascimento=?, CEP=?, Endereco=?, Bairro=?, Cidade=?, UF=?, Tipo=?, Telefone=?, Observacao=?
            WHERE id=?
        """, (
            dados["Nome"], dados["CPF"], dados["DataNascimento"], dados["CEP"], dados["Endereco"], dados["Bairro"],
            dados["Cidade"], dados["UF"], dados["Tipo"], dados["Telefone"], dados["Observacao"], dados["id"]
        ))
    else:
        cursor.execute("""
            INSERT INTO clientes (Nome, CPF, DataNascimento, CEP, Endereco, Bairro, Cidade, UF, Tipo, Telefone, Observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["Nome"], dados["CPF"], dados["DataNascimento"], dados["CEP"], dados["Endereco"], dados["Bairro"],
            dados["Cidade"], dados["UF"], dados["Tipo"], dados["Telefone"], dados["Observacao"]
        ))
    conn.commit()
    conn.close()

# ----------------------------
# Excluir cliente
# ----------------------------
def excluir_cliente_sql(cliente_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    conn.commit()
    conn.close()

# ----------------------------
# Listar clientes
# ----------------------------
def listar_clientes():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes ORDER BY Nome")
    resultados = cursor.fetchall()
    conn.close()
    return resultados

# ----------------------------
# Funções auxiliares para formatação
# ----------------------------
def aplicar_formatacao_cpf(valor):
    """Aplica formatação ao CPF"""
    return formatar_cpf(valor)

def aplicar_formatacao_cep(valor):
    """Aplica formatação ao CEP"""
    return formatar_cep(valor)

def aplicar_formatacao_telefone(valor):
    """Aplica formatação ao telefone"""
    return formatar_telefone(valor)

# ----------------------------
# Inicialização do estado da sessão
# ----------------------------
def inicializar_estado():
    """Inicializa o estado da sessão para clientes"""
    estado_padrao = {
        "clientes_limpar": False,
        "clientes_cpf_raw": "",
        "clientes_cep_raw": "", 
        "clientes_telefone_raw": "",
        "clientes_cpf_formatado": "",
        "clientes_cep_formatado": "",
        "clientes_form_endereco": "",
        "clientes_form_bairro": "",
        "clientes_form_cidade": "",
        "clientes_form_uf": "",
        "clientes_cliente_selecionado": None
    }
    
    for chave, valor in estado_padrao.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor

# ----------------------------
# Limpar campos do formulário
# ----------------------------
def limpar_campos_clientes():
    """Limpa todos os campos do formulário de clientes"""
    campos_para_limpar = [
        "clientes_limpar", "clientes_cpf_raw", "clientes_cep_raw", 
        "clientes_telefone_raw", "clientes_cpf_formatado", 
        "clientes_cep_formatado", "clientes_form_endereco",
        "clientes_form_bairro", "clientes_form_cidade", "clientes_form_uf",
        "clientes_cliente_selecionado"
    ]
    
    for campo in campos_para_limpar:
        if campo == "clientes_limpar":
            st.session_state[campo] = False
        else:
            st.session_state[campo] = ""

# ----------------------------
# Exibir formulário Streamlit
# ----------------------------
def exibir_clientes():
    criar_tabela_clientes()
    inicializar_estado()

    st.markdown("<h2 style='color:#0B3D91'>📋 Cadastro de Clientes</h2>", unsafe_allow_html=True)

    clientes_list = listar_clientes()

    # Seleção de cliente existente
    cliente_selecionado = None
    if clientes_list:
        cliente_opcoes = {f"{c['id']} - {c['Nome']} ({c['CPF']})": c for c in clientes_list}
        escolha = st.selectbox(
            "Selecione um cliente para alterar/excluir (ou deixe em branco para novo):",
            [""] + list(cliente_opcoes.keys())
        )
        if escolha and escolha in cliente_opcoes:
            cliente_selecionado = cliente_opcoes[escolha]
            st.session_state.clientes_cliente_selecionado = cliente_selecionado

    # CORREÇÃO: Container para formatações (FORA do formulário)
    with st.container():
        st.subheader("📝 Dados do Cliente")
        
        col1, col2 = st.columns(2)
        with col1:
            # CPF com formatação manual
            cpf_raw = st.text_input(
                "CPF *",
                value=st.session_state.clientes_cpf_raw,
                key="clientes_cpf_raw_input",
                max_chars=14,
                placeholder="000.000.000-00"
            )
            # Atualizar estado se mudou
            if cpf_raw != st.session_state.clientes_cpf_raw:
                st.session_state.clientes_cpf_raw = cpf_raw
                st.session_state.clientes_cpf_formatado = aplicar_formatacao_cpf(cpf_raw)
        
        with col2:
            # CEP com formatação manual
            cep_raw = st.text_input(
                "CEP",
                value=st.session_state.clientes_cep_raw,
                key="clientes_cep_raw_input",
                max_chars=9,
                placeholder="00000-000"
            )
            # Atualizar estado se mudou
            if cep_raw != st.session_state.clientes_cep_raw:
                st.session_state.clientes_cep_raw = cep_raw
                st.session_state.clientes_cep_formatado = aplicar_formatacao_cep(cep_raw)

        # CORREÇÃO: Botão de busca de CEP (FORA do formulário)
        col_busca1, col_busca2 = st.columns([3, 1])
        with col_busca2:
            if st.button("📌 Buscar CEP", key="clientes_buscar_cep_btn", use_container_width=True):
                cep_para_buscar = st.session_state.clientes_cep_formatado or st.session_state.clientes_cep_raw
                if cep_para_buscar:
                    # CORREÇÃO: Chamada correta da função buscar_endereco_por_cep
                    dados_endereco = buscar_endereco_por_cep(cep_para_buscar)
                    if dados_endereco:
                        st.session_state.clientes_form_endereco = dados_endereco.get("Endereco", "")
                        st.session_state.clientes_form_bairro = dados_endereco.get("Bairro", "")
                        st.session_state.clientes_form_cidade = dados_endereco.get("Cidade", "")
                        st.session_state.clientes_form_uf = dados_endereco.get("UF", "")
                        st.success("✅ Endereço preenchido automaticamente!")
                    else:
                        st.warning("CEP não encontrado.")
                else:
                    st.warning("Informe o CEP primeiro.")

    # CORREÇÃO: Container para telefone (FORA do formulário)
    with st.container():
        st.subheader("📞 Contato")
        
        telefone_raw = st.text_input(
            "Telefone",
            value=st.session_state.clientes_telefone_raw,
            key="clientes_telefone_raw_input",
            max_chars=15,
            placeholder="(00) 00000-0000"
        )
        # Atualizar estado se mudou
        if telefone_raw != st.session_state.clientes_telefone_raw:
            st.session_state.clientes_telefone_raw = telefone_raw

    # CORREÇÃO: Preencher formulário com dados do cliente selecionado
    if cliente_selecionado and not st.session_state.clientes_limpar:
        # Preencher campos apenas uma vez quando o cliente é selecionado
        if st.session_state.clientes_cpf_raw == "":
            st.session_state.clientes_cpf_raw = cliente_selecionado["CPF"] or ""
            st.session_state.clientes_cpf_formatado = aplicar_formatacao_cpf(cliente_selecionado["CPF"] or "")
            st.session_state.clientes_cep_raw = cliente_selecionado["CEP"] or ""
            st.session_state.clientes_cep_formatado = aplicar_formatacao_cep(cliente_selecionado["CEP"] or "")
            st.session_state.clientes_telefone_raw = cliente_selecionado["Telefone"] or ""
            st.session_state.clientes_form_endereco = cliente_selecionado["Endereco"] or ""
            st.session_state.clientes_form_bairro = cliente_selecionado["Bairro"] or ""
            st.session_state.clientes_form_cidade = cliente_selecionado["Cidade"] or ""
            st.session_state.clientes_form_uf = cliente_selecionado["UF"] or ""

    # Formulário principal (SEM modificação de session_state dentro)
    with st.form("form_cliente"):
        # --- Dados pessoais ---
        col1, col2, col3, col4 = st.columns([1,2,1,1])
        
        with col1:
            # CPF formatado (apenas exibição)
            cpf_display = st.text_input(
                "CPF (formatado)",
                value=st.session_state.clientes_cpf_formatado,
                key="clientes_cpf_display",
                disabled=True
            )
            # Campo hidden para o CPF real
            cpf = st.session_state.clientes_cpf_formatado
        
        with col2:
            nome = st.text_input(
                "Nome *",
                value=cliente_selecionado["Nome"] if cliente_selecionado and not st.session_state.clientes_limpar else "",
                key="clientes_nome"
            )
        
        with col3:
            tipo_valor = cliente_selecionado["Tipo"] if cliente_selecionado else "Pessoa Física"
            tipo_index = 0 if tipo_valor == "Pessoa Física" else 1
            tipo = st.selectbox(
                "Tipo *",
                ["Pessoa Física", "Pessoa Jurídica"],
                index=tipo_index,
                key="clientes_tipo"
            )
        
        with col4:
            # Tratamento seguro para datas
            if cliente_selecionado and cliente_selecionado["DataNascimento"] and not st.session_state.clientes_limpar:
                try:
                    data_nascimento_val = pd.to_datetime(cliente_selecionado["DataNascimento"]).date()
                except Exception:
                    data_nascimento_val = date.today()
            else:
                data_nascimento_val = date.today()

            data_nascimento = st.date_input(
                "Data de Nascimento",
                value=data_nascimento_val,
                key="clientes_data_nascimento"
            )

        # --- Endereço ---
        st.subheader("📍 Endereço")
        col1, col2, col3, col4, col5 = st.columns([1,3,2,2,1])
        
        with col1:
            # CEP formatado (apenas exibição)
            cep_display = st.text_input(
                "CEP (formatado)",
                value=st.session_state.clientes_cep_formatado,
                key="clientes_cep_display",
                disabled=True
            )
            # Campo hidden para o CEP real
            cep = st.session_state.clientes_cep_formatado
        
        with col2:
            endereco = st.text_input(
                "Endereço",
                value=st.session_state.clientes_form_endereco,
                key="clientes_endereco"
            )
        
        with col3:
            bairro = st.text_input(
                "Bairro",
                value=st.session_state.clientes_form_bairro,
                key="clientes_bairro"
            )
        
        with col4:
            cidade = st.text_input(
                "Cidade",
                value=st.session_state.clientes_form_cidade,
                key="clientes_cidade"
            )
        
        with col5:
            uf = st.text_input(
                "UF",
                value=st.session_state.clientes_form_uf,
                key="clientes_uf",
                max_chars=2
            ).upper()

        # --- Contato ---
        st.subheader("📞 Contato")
        col1, col2 = st.columns([1,3])
        
        with col1:
            # Telefone formatado (apenas exibição)
            telefone_display = st.text_input(
                "Telefone (formatado)",
                value=aplicar_formatacao_telefone(st.session_state.clientes_telefone_raw),
                key="clientes_telefone_display",
                disabled=True
            )
            # Campo hidden para o telefone real
            telefone = aplicar_formatacao_telefone(st.session_state.clientes_telefone_raw)
        
        with col2:
            obs = st.text_area(
                "Observação",
                value=cliente_selecionado["Observacao"] if cliente_selecionado and not st.session_state.clientes_limpar else "",
                height=80,
                key="clientes_obs"
            )

        # --- Botões ---
        col1, col2, col3, col4 = st.columns([1,1,1,1])  # CORREÇÃO: Adicionada coluna extra
        with col1:
            btn_inserir = st.form_submit_button("➕ Inserir")
        with col2:
            btn_alterar = st.form_submit_button("✏️ Alterar")
        with col3:
            btn_excluir = st.form_submit_button("🗑️ Excluir")
        with col4:  # CORREÇÃO: Botão limpar adicionado
            btn_limpar = st.form_submit_button("✖️ Limpar")

    # CORREÇÃO: Processamento dos botões FORA do formulário
    # --- Dados do cliente para salvar ---
    cliente_dados = {
        "Nome": nome,
        "CPF": cpf,
        "DataNascimento": data_nascimento.strftime("%Y-%m-%d"),
        "CEP": cep,
        "Endereco": endereco,
        "Bairro": bairro,
        "Cidade": cidade,
        "UF": uf,
        "Tipo": tipo,
        "Telefone": telefone,
        "Observacao": obs
    }
    if cliente_selecionado:
        cliente_dados["id"] = cliente_selecionado["id"]

    # --- Inserção ---
    if btn_inserir:
        cpf_valido = validar_cpf(cpf)
        if not nome or not cpf:
            st.error("❌ Nome e CPF são obrigatórios!")
        elif not cpf_valido:
            st.error("❌ CPF inválido!")
        else:
            salvar_cliente_sql(cliente_dados)
            st.success("✅ Cliente inserido com sucesso!")
            st.session_state.clientes_limpar = True
            st.rerun()

    # --- Alteração ---
    if btn_alterar:
        if cliente_selecionado:
            cpf_valido = validar_cpf(cpf)
            if not cpf_valido:
                st.error("❌ CPF inválido!")
            else:
                salvar_cliente_sql(cliente_dados)
                st.success("✅ Cliente alterado com sucesso!")
                st.session_state.clientes_limpar = True
                st.rerun()
        else:
            st.warning("⚠️ Selecione um cliente para alterar.")

    # --- Exclusão ---
    if btn_excluir:
        if cliente_selecionado:
            excluir_cliente_sql(cliente_selecionado["id"])
            st.success("✅ Cliente excluído com sucesso!")
            st.session_state.clientes_limpar = True
            st.rerun()
        else:
            st.warning("⚠️ Selecione um cliente para excluir.")

    # CORREÇÃO: Botão Limpar ---
    if btn_limpar:
        st.session_state.clientes_limpar = True
        st.success("🔄 Formulário limpo!")
        st.rerun()

    # CORREÇÃO: Limpar campos após ação (usando callback seguro)
    if st.session_state.clientes_limpar:
        limpar_campos_clientes()
        st.rerun()

    # Exibir validação do CPF
    if cpf and not validar_cpf(cpf):
        st.error("⚠️ CPF inválido!")

# ----------------------------
# Executar
# ----------------------------
if __name__ == "__main__":
    exibir_clientes()