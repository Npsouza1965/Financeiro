import streamlit as st
import sqlite3
from datetime import datetime, date
import requests
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "nps_financeiro.db")


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
# ----------------------------
# Banco de dados
# ----------------------------
def criar_tabela():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relacionamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_cad DATE,
            tipo TEXT,
            nome TEXT,
            data_nas DATE,
            cnpj_cpf NUMBER,
            cep NUMBER,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            uf TEXT,
            telefone NUMBER,
            email TEXT,
            obs TEXT
        )
    """)
    conn.commit()
    conn.close()

# ----------------------------
# Utilidades
# ----------------------------
def formatar_cpf_cnpj(valor, tipo):
    if not valor:
        return ""
    numeros = re.sub(r'\D', '', valor)
    if tipo == "Cliente" and len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    elif tipo == "Fornecedor" and len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    return valor

def formatar_data_brasil(data_obj):
    """Formata objeto date para string no formato brasileiro"""
    if not data_obj:
        return ""
    return data_obj.strftime("%d/%m/%Y")

def converter_data_sql(data_str):
    """Converte string no formato SQL para date object"""
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").date()
    except:
        return None

def buscar_cep(cep):
    cep = re.sub(r'\D', '', cep or "")
    if len(cep) != 8:
        return None
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "erro" in data:
                return None
            return {
                "endereco": data.get("logradouro", ""),
                "bairro": data.get("bairro", ""),
                "cidade": data.get("localidade", ""),
                "uf": data.get("uf", "")
            }
    except:
        pass
    return None

# ----------------------------
# CRUD
# ----------------------------
def salvar_relacionamento(dados):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO relacionamento (
                data_cad, tipo, nome, data_nas, cnpj_cpf, cep, endereco,
                bairro, cidade, uf, telefone, email, obs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["data_cad"], 
            dados["tipo"], 
            dados["nome"], 
            dados["data_nas"],
            dados["cnpj_cpf"], 
            dados["cep"], 
            dados["endereco"], 
            dados["bairro"],
            dados["cidade"], 
            dados["uf"], 
            dados["telefone"], 
            dados["email"], 
            dados["obs"]
        ))
        conn.commit()
        st.success("✅ Registro incluído com sucesso!")
        return True
    except sqlite3.IntegrityError:
        st.error("❌ Este CPF/CNPJ já está cadastrado!")
        return False
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {e}")
        return False
    finally:
        conn.close()

def atualizar_relacionamento(dados):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE relacionamento SET
                data_cad = ?, tipo = ?, nome = ?, data_nas = ?,
                cep = ?, endereco = ?, bairro = ?, cidade = ?, uf = ?, telefone = ?, email = ?, obs = ?
            WHERE cnpj_cpf = ?
        """, (
            dados["data_cad"], 
            dados["tipo"], 
            dados["nome"], 
            dados["data_nas"],
            dados["cep"], 
            dados["endereco"], 
            dados["bairro"], 
            dados["cidade"],
            dados["uf"], 
            dados["telefone"], 
            dados["email"], 
            dados["obs"], 
            dados["cnpj_cpf"]
        ))
        conn.commit()
        st.success("✅ Registro alterado com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar: {e}")
        return False
    finally:
        conn.close()

def excluir_relacionamento(cnpj_cpf):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM relacionamento WHERE cnpj_cpf = ?", (cnpj_cpf,))
        conn.commit()
        st.success("🗑️ Registro excluído com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao excluir: {e}")
        return False
    finally:
        conn.close()

def listar_registros():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM relacionamento ORDER BY nome")
    rows = cursor.fetchall()
    conn.close()
    return rows

def carregar_registro(cnpj_cpf):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM relacionamento WHERE cnpj_cpf = ?", (cnpj_cpf,))
    row = cursor.fetchone()
    conn.close()
    return row

# ----------------------------
# Formulário principal
# ----------------------------
def formulario_relacionamento():
    st.markdown(
    """
    <h1 style="font-size: 24px; color: #1f77b4; margin-bottom: 30px;">
        📋 Cadastro de Clientes e Fornecedores
    </h1>
    """,
    unsafe_allow_html=True
)
    criar_tabela()

    # Inicializar session_state se não existir
    if "form_initialized" not in st.session_state:
        st.session_state.update({
            "form_data_cad": date.today(),
            "form_tipo": "Cliente",
            "form_nome": "",
            "form_data_nascimento": None,
            "form_cpf_cnpj": "",
            "form_cep": "",
            "form_endereco": "",
            "form_bairro": "",
            "form_cidade": "",
            "form_uf": "",
            "form_telefone": "",
            "form_email": "",
            "form_obs": "",
            "form_initialized": True,
            "selected_record": None,
            "last_selected": ""
        })

    registros = listar_registros()
    registros_str = [f"{r[3]} - {r[5]}" for r in registros]

    # Seleção de registro existente
    selecionado = st.selectbox("Selecionar registro para edição/exclusão", [""] + registros_str, key="select_registro")
    
    # CORREÇÃO: Verificar se houve mudança na seleção
    if selecionado and selecionado != st.session_state.get("last_selected", ""):
        idx = registros_str.index(selecionado)
        registro = registros[idx]
        
        # Converter datas do banco (formato SQL) para objetos date
        data_cad = converter_data_sql(registro[1])
        data_nas = converter_data_sql(registro[4])

        # Atualizar session_state
        st.session_state.update({
            "form_data_cad": data_cad if data_cad else date.today(),
            "form_tipo": registro[2],
            "form_nome": registro[3],
            "form_data_nascimento": data_nas,
            "form_cpf_cnpj": registro[5],
            "form_cep": str(registro[6] or ""),
            "form_endereco": registro[7],
            "form_bairro": registro[8],
            "form_cidade": registro[9],
            "form_uf": registro[10],
            "form_telefone": str(registro[11] or ""),
            "form_email": registro[12],
            "form_obs": registro[13],
            "selected_record": registro[5],
            "last_selected": selecionado
        })

    with st.form("form_relacionamento", clear_on_submit=False):
        # CORREÇÃO: Layout organizado em seções
        
        # Seção 1: Dados Básicos
        styled_subheader("📝 Dados Básicos", "14px")
        col1, col2 = st.columns(2)
        
        with col1:
            data_cadastro = st.date_input(
                "Data de Cadastro *",
                value=st.session_state.get("form_data_cad", date.today()),
                key="data_cad_input",
                format="DD/MM/YYYY"
            )
        
        with col2:
            tipo = st.selectbox(
                "Tipo *", 
                ["Cliente", "Fornecedor"], 
                index=0 if st.session_state.get("form_tipo") == "Cliente" else 1,
                key="tipo_input"
            )
        
        nome = st.text_input(
            "Nome Completo *", 
            value=st.session_state.get("form_nome", ""), 
            key="nome_input",
            placeholder="Digite o nome completo"
        )

        # Seção 2: Documentos e Contato
        styled_subheader("📄 Documentos e Contato", "14px")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_nascimento = st.date_input(
                "Data de Nascimento",
                value=st.session_state.get("form_data_nascimento"),
                key="data_nascimento_input",
                format="DD/MM/YYYY"
            )
                
        with col2:
            cnpj_cpf_input = st.text_input(
                "CPF/CNPJ *", 
                value=st.session_state.get("form_cpf_cnpj", ""), 
                key="cpf_cnpj_input",
                placeholder="000.000.000-00 ou 00.000.000/0000-00"
            )
            # Formatar automaticamente
            if cnpj_cpf_input and cnpj_cpf_input != st.session_state.get("last_cpf_cnpj", ""):
                cnpj_cpf_formatado = formatar_cpf_cnpj(cnpj_cpf_input, tipo)
                if cnpj_cpf_formatado != cnpj_cpf_input:
                    st.session_state.form_cpf_cnpj = cnpj_cpf_formatado
                    st.session_state.last_cpf_cnpj = cnpj_cpf_formatado
                    st.rerun()
                
        with col3:
            cep = st.text_input(
                "CEP", 
                value=st.session_state.get("form_cep", ""), 
                key="cep_input",
                placeholder="00000-000"
            )
            if cep and len(re.sub(r'\D', '', cep)) == 8 and cep != st.session_state.get("last_cep", ""):
                dados_cep = buscar_cep(cep)
                if dados_cep:
                    st.session_state.form_endereco = dados_cep["endereco"]
                    st.session_state.form_bairro = dados_cep["bairro"]
                    st.session_state.form_cidade = dados_cep["cidade"]
                    st.session_state.form_uf = dados_cep["uf"]
                    st.session_state.last_cep = cep
                    st.rerun()

        # Seção 3: Endereço
        styled_subheader("🏠 Endereço", "14px")
        endereco = st.text_input(
            "Endereço", 
            value=st.session_state.get("form_endereco", ""), 
            key="endereco_input",
            placeholder="Rua, Avenida, etc."
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            bairro = st.text_input(
                "Bairro", 
                value=st.session_state.get("form_bairro", ""), 
                key="bairro_input"
            )
        with col2:
            cidade = st.text_input(
                "Cidade", 
                value=st.session_state.get("form_cidade", ""), 
                key="cidade_input"
            )
        with col3:
            uf = st.text_input(
                "UF", 
                value=st.session_state.get("form_uf", ""), 
                key="uf_input",
                placeholder="SP, RJ, MG, etc.",
                max_chars=2
            )

        # Seção 4: Contato
        styled_subheader("📞 Contato","14px")
        col1, col2 = st.columns(2)
        
        with col1:
            telefone = st.text_input(
                "Telefone", 
                value=st.session_state.get("form_telefone", ""), 
                key="telefone_input",
                placeholder="(00) 00000-0000"
            )
        
        with col2:
            email = st.text_input(
                "Email", 
                value=st.session_state.get("form_email", ""), 
                key="email_input",
                placeholder="seu@email.com"
            )

        # Seção 5: Observações
        styled_subheader("📋 Observações", "14px")
        obs = st.text_area(
            "Observações", 
            value=st.session_state.get("form_obs", ""), 
            key="obs_input",
            placeholder="Informações adicionais...",
            height=100
        )

        st.markdown("---")
        
        # Botões
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            incluir = st.form_submit_button("💾 Incluir", use_container_width=True)
        with c2:
            alterar = st.form_submit_button("✏️ Alterar", use_container_width=True)
        with c3:
            excluir = st.form_submit_button("🗑️ Excluir", use_container_width=True)
        with c4:
            limpar = st.form_submit_button("🧹 Limpar", use_container_width=True)

    # CORREÇÃO: Processar ações FORA do form para evitar duplicação
    if 'incluir' in locals() and incluir:
        if not nome.strip():
            st.error("❌ O campo Nome é obrigatório!")
        else:
            # CORREÇÃO CRÍTICA: Garantir que data_nas seja salva corretamente
            data_nas_str = data_nascimento.strftime("%Y-%m-%d") if data_nascimento else None
            
            # DEBUG: Mostrar o que está sendo salvo
            st.write(f"🔍 DEBUG - Data nascimento sendo salva: {data_nas_str}")
            
            dados = {
                "data_cad": data_cadastro.strftime("%Y-%m-%d"),
                "tipo": tipo, 
                "nome": nome.strip(),
                "data_nas": data_nas_str,  # CORREÇÃO: Agora salva corretamente
                "cnpj_cpf": re.sub(r'\D', '', st.session_state.get("form_cpf_cnpj", "")),
                "cep": re.sub(r'\D', '', cep) if cep else "",
                "endereco": endereco.strip(), 
                "bairro": bairro.strip(),
                "cidade": cidade.strip(), 
                "uf": uf.strip().upper(), 
                "telefone": re.sub(r'\D', '', telefone) if telefone else "",
                "email": email.strip(), 
                "obs": obs.strip()
            }
            
            if salvar_relacionamento(dados):
                # Limpar session_state após salvar
                for key in ["form_nome", "form_data_nascimento", "form_cpf_cnpj", "form_cep", 
                           "form_endereco", "form_bairro", "form_cidade", "form_uf", 
                           "form_telefone", "form_email", "form_obs", "selected_record", "last_selected"]:
                    if key in st.session_state:
                        if key == "form_data_nascimento":
                            st.session_state[key] = None
                        else:
                            st.session_state[key] = ""
                
                st.session_state.form_data_cad = date.today()
                st.session_state.form_tipo = "Cliente"
                st.rerun()

    if 'alterar' in locals() and alterar and st.session_state.get("selected_record"):
        if not nome:
            st.error("❌ Nome é obrigatório!")
        else:
            # CORREÇÃO CRÍTICA: Garantir que data_nas seja salva corretamente
            data_nas_str = data_nascimento.strftime("%Y-%m-%d") if data_nascimento else None
            
            st.write(f"🔍 DEBUG - Data nascimento sendo atualizada: {data_nas_str}")
            
            dados = {
                "data_cad": data_cadastro.strftime("%Y-%m-%d"),
                "tipo": tipo, 
                "nome": nome.strip(),
                "data_nas": data_nas_str,  # CORREÇÃO: Agora salva corretamente
                "cnpj_cpf": st.session_state.selected_record,  # Mantém o CNPJ/CPF original para WHERE
                "cep": re.sub(r'\D', '', cep) if cep else "",
                "endereco": endereco.strip(), 
                "bairro": bairro.strip(),
                "cidade": cidade.strip(), 
                "uf": uf.strip().upper(), 
                "telefone": re.sub(r'\D', '', telefone) if telefone else "",
                "email": email.strip(), 
                "obs": obs.strip()
            }
            
            if atualizar_relacionamento(dados):
                st.rerun()

    if 'excluir' in locals() and excluir and st.session_state.get("selected_record"):
        if excluir_relacionamento(st.session_state.selected_record):
            for key in list(st.session_state.keys()):
                if key.startswith("form_"):
                    if key == "form_data_cad":
                        st.session_state[key] = date.today()
                    elif key == "form_tipo":
                        st.session_state[key] = "Cliente"
                    elif key == "form_data_nascimento":
                        st.session_state[key] = None
                    else:
                        st.session_state[key] = ""
            st.session_state.selected_record = None
            st.session_state.last_selected = ""
            st.rerun()

    if 'limpar' in locals() and limpar:
        for key in list(st.session_state.keys()):
            if key.startswith("form_"):
                if key == "form_data_cad":
                    st.session_state[key] = date.today()
                elif key == "form_tipo":
                    st.session_state[key] = "Cliente"
                elif key == "form_data_nascimento":
                    st.session_state[key] = None
                else:
                    st.session_state[key] = ""
        st.session_state.selected_record = None
        st.session_state.last_selected = ""
        st.rerun()

    # Verificar dados no banco
    if st.checkbox("📊 Ver dados salvos no banco", False):
        st.write("Últimos 5 registros:")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, data_cad, data_nas, cnpj_cpf FROM relacionamento ORDER BY id DESC LIMIT 5")
        registros_db = cursor.fetchall()
        conn.close()
        
        for registro in registros_db:
            st.write(f"**{registro[0]}** - CPF: {registro[3]} - Cad: {registro[1]} - Nasc: {registro[2]}")