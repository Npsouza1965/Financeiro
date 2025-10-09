import streamlit as st
import sqlite3
import base64
import re
import unicodedata
from Formatacao import (
    formatar_cep,
    formatar_telefone,
    formatar_cnpj,
    validar_cnpj,
    buscar_endereco_por_cep
)

DB_FILE = "financeiro.db"

# ----------------------------
# Normalização de texto
# ----------------------------
def normalizar_texto(texto):
    """Remove espaços extras e normaliza acentos e caracteres especiais"""
    return unicodedata.normalize('NFC', texto.strip()) if texto else ""


# ----------------------------
# Conexão com banco
# ----------------------------
def conectar_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------
# CRUD
# ----------------------------
def listar_fornecedores():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MIN(id) as id, cnpj, nome, cep, endereco, numero, bairro, cidade, uf, telefone, email, observacoes
        FROM fornecedores
        GROUP BY nome
        ORDER BY nome COLLATE NOCASE
    """)
    resultados = cursor.fetchall()
    conn.close()
    return resultados


def inserir_fornecedor(dados):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fornecedores (cnpj, nome, cep, endereco, numero, bairro, cidade, uf, telefone, email, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados["cnpj"], dados["nome"], dados.get("cep", ""), dados.get("endereco", ""),
        dados.get("numero", ""), dados.get("bairro", ""), dados.get("cidade", ""),
        dados.get("uf", ""), dados.get("telefone", ""), dados.get("email", ""),
        dados.get("observacoes", "")
    ))
    conn.commit()
    conn.close()


def atualizar_fornecedor(id, dados):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE fornecedores SET
        cnpj=?, nome=?, cep=?, endereco=?, numero=?, bairro=?, cidade=?, uf=?, telefone=?, email=?, observacoes=?
        WHERE id=?
    """, (
        dados["cnpj"], dados["nome"], dados.get("cep", ""), dados.get("endereco", ""),
        dados.get("numero", ""), dados.get("bairro", ""), dados.get("cidade", ""),
        dados.get("uf", ""), dados.get("telefone", ""), dados.get("email", ""),
        dados.get("observacoes", ""), id
    ))
    conn.commit()
    conn.close()


def excluir_fornecedor(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fornecedores WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ----------------------------
# Limpar formulário
# ----------------------------
def limpar_formulario():
    st.session_state.update({
        "form_id": "",
        "form_cnpj": "",
        "form_nome": "",
        "form_cep": "",
        "form_endereco": "",
        "form_numero": "",
        "form_bairro": "",
        "form_cidade": "",
        "form_uf": "",
        "form_telefone": "",
        "form_email": "",
        "form_observacoes": ""
    })


# ----------------------------
# Normalizar CEP
# ----------------------------
def normalizar_cep(cep: str) -> str:
    """Remove tudo que não for dígito e retorna string limpa."""
    if not cep:
        return ""
    return re.sub(r"\D", "", str(cep).strip())

# ----------------------------
# Funções de formatação manual (sem callbacks)
# ----------------------------
def aplicar_formatacao_cnpj(valor):
    """Aplica formatação ao CNPJ manualmente"""
    return formatar_cnpj(valor)

def aplicar_formatacao_cep(valor):
    """Aplica formatação ao CEP manualmente"""
    return formatar_cep(valor)

def aplicar_formatacao_telefone(valor):
    """Aplica formatação ao telefone manualmente"""
    return formatar_telefone(valor)

# ----------------------------
# Interface principal
# ----------------------------
def exibir_fornecedores():
    st.header("📋 Cadastro de Fornecedores")

    # Inicializa flags
    if "limpar_form" not in st.session_state:
        st.session_state["limpar_form"] = False

    # Lista de fornecedores
    fornecedores = listar_fornecedores()
    fornecedor_selecionado = None

    if fornecedores:
        opcoes = {
            str(f["id"]): f"{normalizar_texto(f['nome'] or '')} ({str(f['cnpj'] or '').strip()})"
            for f in fornecedores
        }

        escolha = st.selectbox(
            "Selecione um fornecedor para alterar/excluir:",
            [""] + list(opcoes.keys()),
            format_func=lambda x: opcoes.get(x, "")
        )

        if escolha and escolha in opcoes:
            fornecedor_selecionado = next((f for f in fornecedores if str(f["id"]) == escolha), None)
            if fornecedor_selecionado:
                for key in [
                    "id", "cnpj", "nome", "cep", "endereco", "numero",
                    "bairro", "cidade", "uf", "telefone", "email", "observacoes"
                ]:
                    valor = fornecedor_selecionado[key] or ""
                    st.session_state[f"form_{key}"] = str(valor)

    # Limpar formulário
    if st.session_state["limpar_form"]:
        limpar_formulario()
        st.session_state["limpar_form"] = False

    # CORREÇÃO: Campos de formatação manual (FORA do formulário)
    if "cnpj_raw" not in st.session_state:
        st.session_state.cnpj_raw = st.session_state.get("form_cnpj", "")
    if "cep_raw" not in st.session_state:
        st.session_state.cep_raw = st.session_state.get("form_cep", "")
    if "telefone_raw" not in st.session_state:
        st.session_state.telefone_raw = st.session_state.get("form_telefone", "")

    # Container para formatações manuais
    with st.container():
        st.subheader("📝 Dados do Fornecedor")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CNPJ com formatação manual
            cnpj_raw = st.text_input(
                "CNPJ *",
                value=st.session_state.cnpj_raw,
                key="cnpj_raw_input",
                max_chars=18,
                placeholder="00.000.000/0000-00"
            )
            if cnpj_raw != st.session_state.cnpj_raw:
                st.session_state.cnpj_raw = cnpj_raw
                st.session_state.cnpj_formatado = aplicar_formatacao_cnpj(cnpj_raw)
                st.rerun()
            
            # Validação do CNPJ
            cnpj_limpo = re.sub(r'\D', '', st.session_state.get("cnpj_formatado", ""))
            if cnpj_limpo and len(cnpj_limpo) == 14:
                if not validar_cnpj(st.session_state.get("cnpj_formatado", "")):
                    st.error("❌ CNPJ inválido!")
        
        with col2:
            nome = st.text_input(
                "Nome *",
                value=st.session_state.get("form_nome", ""),
                key="nome_input"
            )
            if nome != st.session_state.get("form_nome", ""):
                st.session_state.form_nome = nome

    # Busca de CNPJ (FORA do formulário)
    cnpj_limpo = re.sub(r'\D', '', st.session_state.get("cnpj_formatado", ""))
    if cnpj_limpo and len(cnpj_limpo) == 14 and validar_cnpj(st.session_state.get("cnpj_formatado", "")):
        if st.button("🔍 Buscar dados pelo CNPJ", key="buscar_cnpj_btn"):
            # Verificar se CNPJ já existe
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fornecedores WHERE cnpj = ?", (cnpj_limpo,))
            fornecedor_existente = cursor.fetchone()
            conn.close()
            
            if fornecedor_existente:
                st.warning("⚠️ CNPJ já cadastrado!")
                # Preencher formulário com dados existentes
                for key in ["id", "cnpj", "nome", "cep", "endereco", "numero", "bairro", "cidade", "uf", "telefone", "email", "observacoes"]:
                    st.session_state[f"form_{key}"] = str(fornecedor_existente[key] or "")
                st.session_state.cnpj_formatado = formatar_cnpj(fornecedor_existente["cnpj"] or "")
                st.session_state.cep_raw = fornecedor_existente["cep"] or ""
                st.session_state.telefone_raw = fornecedor_existente["telefone"] or ""
                st.rerun()

    # Container para CEP (FORA do formulário)
    with st.container():
        st.subheader("📍 Endereço")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            # CEP com formatação manual
            cep_raw = st.text_input(
                "CEP",
                value=st.session_state.cep_raw,
                key="cep_raw_input",
                max_chars=9,
                placeholder="00000-000"
            )
            if cep_raw != st.session_state.cep_raw:
                st.session_state.cep_raw = cep_raw
                st.session_state.cep_formatado = aplicar_formatacao_cep(cep_raw)
                st.rerun()
        
        with col2:
            if st.button("📌 Buscar CEP", key="buscar_cep_btn"):
                cep_para_buscar = st.session_state.get("cep_formatado", "") or st.session_state.get("cep_raw", "")
                if cep_para_buscar:
                    dados_endereco = buscar_endereco_por_cep(cep_para_buscar)
                    if dados_endereco:
                        st.session_state["form_endereco"] = dados_endereco.get("Endereco", "")
                        st.session_state["form_bairro"] = dados_endereco.get("Bairro", "")
                        st.session_state["form_cidade"] = dados_endereco.get("Cidade", "")
                        st.session_state["form_uf"] = dados_endereco.get("UF", "")
                        st.success("✅ Endereço preenchido automaticamente!")
                        st.rerun()
                    else:
                        st.warning("CEP não encontrado.")
                else:
                    st.warning("Informe o CEP primeiro.")

    # Container para telefone (FORA do formulário)
    with st.container():
        st.subheader("📞 Contato")
        
        telefone_raw = st.text_input(
            "Telefone",
            value=st.session_state.telefone_raw,
            key="telefone_raw_input",
            max_chars=15,
            placeholder="(00) 00000-0000"
        )
        if telefone_raw != st.session_state.telefone_raw:
            st.session_state.telefone_raw = telefone_raw
            st.session_state.telefone_formatado = aplicar_formatacao_telefone(telefone_raw)

    # ----------------------------
    # 🔹 Formulário principal (SEM callbacks)
    # ----------------------------
    with st.form("form_fornecedor"):
        # Campos hidden para valores formatados
        cnpj = st.session_state.get("cnpj_formatado", "")
        cep = st.session_state.get("cep_formatado", "")
        telefone = st.session_state.get("telefone_formatado", "")
        
        # Exibir campos formatados (somente leitura)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("CNPJ (formatado)", value=cnpj, key="cnpj_display", disabled=True)
        with col2:
            st.text_input("CEP (formatado)", value=cep, key="cep_display", disabled=True)
        
        # Endereço
        col1, col2 = st.columns(2)
        with col1:
            endereco = st.text_input("Endereço", value=st.session_state.get("form_endereco", ""), key="form_endereco")
        with col2:
            numero = st.text_input("Número", value=st.session_state.get("form_numero", ""), key="form_numero", max_chars=18)

        col3, col4, col5 = st.columns(3)
        with col3:
            bairro = st.text_input("Bairro", value=st.session_state.get("form_bairro", ""), key="form_bairro")
        with col4:
            cidade = st.text_input("Cidade", value=st.session_state.get("form_cidade", ""), key="form_cidade")
        with col5:
            uf = st.text_input("UF", value=st.session_state.get("form_uf", ""), key="form_uf", max_chars=2).upper()

        # Contato
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Telefone (formatado)", value=telefone, key="telefone_display", disabled=True)
        with col2:
            email = st.text_input("Email", value=st.session_state.get("form_email", ""), key="form_email")

        observacoes = st.text_area("Observações", value=st.session_state.get("form_observacoes", ""), key="form_observacoes", height=50)

        # ----------------------------
        # Botões principais
        # ----------------------------
        colb1, colb2, colb3, colb4 = st.columns(4)
        with colb1:
            inserir = st.form_submit_button("➕ Inserir")
        with colb2:
            alterar = st.form_submit_button("✏️ Alterar")
        with colb3:
            excluir = st.form_submit_button("🗑️ Excluir")
        with colb4:
            limpar = st.form_submit_button("✖️ Limpar")

        # ----------------------------
        # Processamento dos botões
        # ----------------------------
        form_data = {
            "cnpj": cnpj,
            "nome": nome,
            "cep": cep,
            "endereco": endereco,
            "numero": numero,
            "bairro": bairro,
            "cidade": cidade,
            "uf": uf,
            "telefone": telefone,
            "email": email,
            "observacoes": observacoes
        }

        if limpar:
            st.session_state["limpar_form"] = True
            # Limpar campos de formatação
            st.session_state.cnpj_raw = ""
            st.session_state.cep_raw = ""
            st.session_state.telefone_raw = ""
            st.session_state.cnpj_formatado = ""
            st.session_state.cep_formatado = ""
            st.session_state.telefone_formatado = ""
            st.rerun()

        elif inserir:
            # Validar campos obrigatórios
            if not cnpj or not nome:
                st.error("❌ CNPJ e Nome são campos obrigatórios!")
            elif cnpj and not validar_cnpj(cnpj):
                st.error("❌ CNPJ inválido!")
            else:
                inserir_fornecedor(form_data)
                st.success("✅ Fornecedor inserido com sucesso!")
                st.session_state["limpar_form"] = True
                # Limpar campos de formatação
                st.session_state.cnpj_raw = ""
                st.session_state.cep_raw = ""
                st.session_state.telefone_raw = ""
                st.session_state.cnpj_formatado = ""
                st.session_state.cep_formatado = ""
                st.session_state.telefone_formatado = ""
                st.rerun()

        elif alterar and fornecedor_selecionado:
            if not cnpj or not nome:
                st.error("❌ CNPJ e Nome são campos obrigatórios!")
            elif cnpj and not validar_cnpj(cnpj):
                st.error("❌ CNPJ inválido!")
            else:
                atualizar_fornecedor(fornecedor_selecionado["id"], form_data)
                st.success("✅ Fornecedor atualizado com sucesso!")
                st.session_state["limpar_form"] = True
                # Limpar campos de formatação
                st.session_state.cnpj_raw = ""
                st.session_state.cep_raw = ""
                st.session_state.telefone_raw = ""
                st.session_state.cnpj_formatado = ""
                st.session_state.cep_formatado = ""
                st.session_state.telefone_formatado = ""
                st.rerun()

        elif excluir and fornecedor_selecionado:
            excluir_fornecedor(fornecedor_selecionado["id"])
            st.success("✅ Fornecedor excluído com sucesso!")
            st.session_state["limpar_form"] = True
            # Limpar campos de formatação
            st.session_state.cnpj_raw = ""
            st.session_state.cep_raw = ""
            st.session_state.telefone_raw = ""
            st.session_state.cnpj_formatado = ""
            st.session_state.cep_formatado = ""
            st.session_state.telefone_formatado = ""
            st.rerun()

if __name__ == "__main__":
    exibir_fornecedores()