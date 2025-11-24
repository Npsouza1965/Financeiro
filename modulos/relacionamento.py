import streamlit as st
import sqlite3
import requests
import re
import os
import sys
from formatacao import validar_cpf, validar_cnpj
from config import DB_FILE
import datetime
from datetime import date

# Onde conecta ao banco:
conn = sqlite3.connect(DB_FILE)

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

def aplicar_estilos_inputs():
    """Aplica estilos para controlar a largura e altura dos inputs"""
    st.markdown("""
        <style>
        /* CONTROLE GERAL DA LARGURA DOS INPUTS - CAMPOS EXPANSÍVEIS */
        .stTextInput > div > div > input {
            width: 100% !important;
            min-width: 180px !important;
            max-width: 100% !important;
        }
        
        .stTextArea > div > div > textarea {
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
        }
        
        .stDateInput > div > div > input {
            width: 100% !important;
            min-width: 150px !important;
            font-size: 14px !important;
        }
        
        .stSelectbox > div > div > select {
            width: 100% !important;
            min-width: 150px !important;
            font-size: 14px !important;
        }
        
        /* ESPAÇAMENTO ENTRE CAMPOS - REDUZIDO */
        .stTextInput, .stDateInput, .stSelectbox, .stTextArea {
            margin-bottom: 5px !important;
        }
        
        /* ALTURA DOS INPUTS - 40px */
        .stTextInput > div > div > input {
            height: 40px !important;
            padding: 4px 8px !important;
            font-size: 14px !important;
        }
        
        .stTextArea > div > div > textarea {
            min-height: 80px !important;
            padding: 4px 8px !important;
            font-size: 14px !important;
        }
        
        .stDateInput > div > div > input {
            height: 40px !important;
            padding: 4px 8px !important;
        }
        
        .stSelectbox > div > div > select {
            height: 80px !important;
            padding: 4px 8px !important;
        }
        
        /* FOCO NOS INPUTS */
        .stTextInput > div > div > input:focus {
            border-color: #171ae0 !important;
            box-shadow: 0 0 0 1px #171ae0 !important;
        }
        
        /* CONTAINER DO FORMULÁRIO - MAIS COMPACTO */
        .form-container {
            background-color: #f8f9fa;
            padding: 15px !important;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 10px !important;
        }
        
        /* CLASSES PARA LARGURAS ESPECÍFICAS - REMOVIDOS LIMITES MÁXIMOS */
        .input-minimo .stTextInput > div > div > input {
            min-width: 80px !important;
            max-width: none !important;
        }
        
        .input-pequeno .stTextInput > div > div > input {
            min-width: 120px !important;
            max-width: none !important;
        }
        
        .input-medio .stTextInput > div > div > input {
            min-width: 180px !important;
            max-width: none !important;
        }
        
        .input-grande .stTextInput > div > div > input {
            min-width: 250px !important;
            max-width: none !important;
        }
        
        .input-full .stTextInput > div > div > input {
            min-width: 100% !important;
            max-width: 100% !important;
        }
        
        /* BOTÕES COM MELHOR APARÊNCIA */
        .stButton > button {
            height: 32px !important;
            font-weight: 500 !important;
            font-size: 14px !important;
        }
        
        /* LABELS MAIS COMPACTOS */
        .stTextInput label, .stDateInput label, .stSelectbox label, .stTextArea label {
            font-size: 14px !important;
            margin-bottom: 2px !important;
            font-weight: 500 !important;
        }

        /* ALINHAMENTO CORRETO DO BOTÃO BUSCAR CEP - SUPERIOR COM SUPERIOR */
        .align-button-top {
            display: flex;
            align-items: flex-start !important;
            justify-content: flex-start;
            padding-top: 0 !important;
            margin-top: 0 !important;
            height: auto !important;
        }
        
        .align-button-top button {
            margin-top: 1.6rem !important;
            align-self: flex-start !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ----------------------------
# Banco de dados
# ----------------------------
def criar_tabela():
    """Cria a tabela se não existir"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relacionamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_cad DATE,
            tipo TEXT,
            nome TEXT,
            data_nas DATE,
            cnpj_cpf TEXT UNIQUE,
            cep TEXT,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            uf TEXT,
            telefone TEXT,
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

def converter_data_sql(data_str):
    if not data_str:
        return None
    try:
        return datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
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
            dados["data_cad"], dados["tipo"], dados["nome"], dados["data_nas"],
            dados["cnpj_cpf"], dados["cep"], dados["endereco"], dados["bairro"],
            dados["cidade"], dados["uf"], dados["telefone"], dados["email"], dados["obs"]
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

def atualizar_relacionamento(dados, id_registro):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE relacionamento SET
                data_cad = ?, tipo = ?, nome = ?, data_nas = ?,
                cnpj_cpf = ?, cep = ?, endereco = ?, bairro = ?, cidade = ?, uf = ?, 
                telefone = ?, email = ?, obs = ?
            WHERE id = ?
        """, (
            dados["data_cad"], dados["tipo"], dados["nome"], dados["data_nas"],
            dados["cnpj_cpf"], dados["cep"], dados["endereco"], dados["bairro"], 
            dados["cidade"], dados["uf"], dados["telefone"], dados["email"], 
            dados["obs"], id_registro
        ))
        conn.commit()
        st.success("✅ Registro alterado com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar: {e}")
        return False
    finally:
        conn.close()

def excluir_relacionamento(id_registro):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM relacionamento WHERE id = ?", (id_registro,))
        conn.commit()
        if cursor.rowcount > 0:
            st.success("🗑️ Registro excluído com sucesso!")
            return True
        else:
            st.error("❌ Registro não encontrado!")
            return False
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

def carregar_registro_por_id(id_registro):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM relacionamento WHERE id = ?", (id_registro,))
    row = cursor.fetchone()
    conn.close()
    return row

# ----------------------------
# Formulário principal - COMPACTADO
# ----------------------------
def formulario_relacionamento():
    # APLICAR ESTILOS DE LARGURA E ALTURA
    aplicar_estilos_inputs()
    
    st.markdown(
        """
        <h1 style="font-size: 26px; color: #171ae0; margin-bottom: 15px; text-align: center;">
            📋 Cadastro de Clientes e Fornecedores
        </h1>
        """,
        unsafe_allow_html=True
    )
    
    criar_tabela()
    
    # Inicializar session_state
    if 'editando_id' not in st.session_state:
        st.session_state.editando_id = None
        st.session_state.form_data = {
            'data_cad': date.today(),
            'tipo': 'Cliente',
            'nome': '',
            'data_nas': None,
            'cnpj_cpf': '',
            'cep': '',
            'endereco': '',
            'bairro': '',
            'cidade': '',
            'uf': '',
            'telefone': '',
            'email': '',
            'obs': ''
        }
    
    # Lista de registros para o combobox
    registros = listar_registros()
    opcoes_select = ["Novo registro"] + [f"{r[0]} - {r[3]} - {r[5]}" for r in registros]
    
    # Seção de seleção de registro
    with st.container():
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            selecao = st.selectbox("**Selecionar registro para edição/exclusão**", opcoes_select)
        with col2:
            # Botão alinhado no topo
            st.markdown('<div class="align-button-top">', unsafe_allow_html=True)
            if st.button("🔄 Atualizar Lista", use_container_width=True):
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Processar seleção do combobox
    if selecao != "Novo registro":
        id_selecionado = int(selecao.split(" - ")[0])
        if st.session_state.editando_id != id_selecionado:
            registro = carregar_registro_por_id(id_selecionado)
            if registro:
                st.session_state.editando_id = id_selecionado
                st.session_state.form_data = {
                    'data_cad': converter_data_sql(registro[1]) or date.today(),
                    'tipo': registro[2],
                    'nome': registro[3],
                    'data_nas': converter_data_sql(registro[4]),
                    'cnpj_cpf': registro[5],
                    'cep': registro[6] or '',
                    'endereco': registro[7] or '',
                    'bairro': registro[8] or '',
                    'cidade': registro[9] or '',
                    'uf': registro[10] or '',
                    'telefone': registro[11] or '',
                    'email': registro[12] or '',
                    'obs': registro[13] or ''
                }
    else:
        if st.session_state.editando_id is not None:
            st.session_state.editando_id = None
            st.session_state.form_data = {
                'data_cad': date.today(),
                'tipo': 'Cliente',
                'nome': '',
                'data_nas': None,
                'cnpj_cpf': '',
                'cep': '',
                'endereco': '',
                'bairro': '',
                'cidade': '',
                'uf': '',
                'telefone': '',
                'email': '',
                'obs': ''
            }
    
    # FORMULÁRIO PRINCIPAL - MAIS COMPACTO
    with st.form("form_cadastro"):
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        # SEÇÃO 1: DADOS BÁSICOS
        styled_subheader("👤 Dados Básicos")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_cad = st.date_input(
                "Data de Cadastro",
                value=st.session_state.form_data['data_cad'],
                format="DD/MM/YYYY"
            )
        
        with col2:
            tipo = st.selectbox(
                "Tipo", 
                ["Cliente", "Fornecedor"], 
                index=0 if st.session_state.form_data['tipo'] == "Cliente" else 1
            )
        
        with col3:
            data_nas = st.date_input(
                "Data Nasc.",
                value=st.session_state.form_data['data_nas'],
                format="DD/MM/YYYY",
                min_value=datetime.date(1900, 1, 1)
            )
        
        # NOME
        nome = st.text_input(
            "Nome Completo/Razão Social *", 
            value=st.session_state.form_data['nome'],
            placeholder="",
            max_chars=200
        )

        # SEÇÃO 2: DOCUMENTOS
        styled_subheader("📄 Documentos")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            cnpj_cpf = st.text_input(
                "CPF/CNPJ *", 
                value=st.session_state.form_data['cnpj_cpf'],
                placeholder="",
                key="cnpj_cpf_input",
                max_chars=18
            )
            
            # Validação em tempo real
            if cnpj_cpf:
                cnpj_cpf_limpo = ''.join(filter(str.isdigit, cnpj_cpf))
                
                if len(cnpj_cpf_limpo) == 11:
                    if validar_cpf(cnpj_cpf_limpo):
                        st.success("✅ CPF válido")
                    else:
                        st.error("❌ CPF inválido")
                elif len(cnpj_cpf_limpo) == 14:
                    if validar_cnpj(cnpj_cpf_limpo):
                        st.success("✅ CNPJ válido")
                    else:
                        st.error("❌ CNPJ inválido")
                else:
                    st.warning("⚠️ CPF (11) ou CNPJ (14) dígitos")
        
        with col2:
            cep = st.text_input(
                "CEP", 
                value=st.session_state.form_data['cep'],
                placeholder="00000-000",
                max_chars=9
            )
        
        with col3:
            # Botão alinhado no TOPO com os campos
            st.markdown('<div class="align-button-top">', unsafe_allow_html=True)
            btn_buscar_cep = st.form_submit_button("🔍 Buscar CEP", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # SEÇÃO 3: ENDEREÇO
        styled_subheader("🏠 Endereço")
        
        endereco = st.text_input(
            "Logradouro", 
            value=st.session_state.form_data['endereco'],
            placeholder="",
            max_chars=200
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            bairro = st.text_input(
                "Bairro", 
                value=st.session_state.form_data['bairro'],
                placeholder="",
                max_chars=50
            )
            
        with col2:
            cidade = st.text_input(
                "Cidade", 
                value=st.session_state.form_data['cidade'],
                placeholder="",
                max_chars=50
            )
            
        with col3:
            uf = st.text_input(
                "UF", 
                value=st.session_state.form_data['uf'],
                placeholder="",
                max_chars=2
            ).upper()

        # SEÇÃO 4: CONTATOS
        styled_subheader("📞 Contatos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            telefone = st.text_input(
                "Telefone", 
                value=st.session_state.form_data['telefone'],
                placeholder="",
                max_chars=15
            )
        
        with col2:
            email = st.text_input(
                "E-mail", 
                value=st.session_state.form_data['email'],
                placeholder="",
                max_chars=100
            )

        # SEÇÃO 5: OBSERVAÇÕES
        styled_subheader("📋 Observações")
        
        obs = st.text_area(
            "Observações", 
            value=st.session_state.form_data['obs'],
            placeholder="",
            height=80,
            max_chars=500
        )

        st.markdown('</div>', unsafe_allow_html=True)
        
        # BOTÕES DE AÇÃO
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            btn_incluir = st.form_submit_button("💾 Incluir", use_container_width=True)
        with col2:
            btn_alterar = st.form_submit_button("✏️ Alterar", use_container_width=True,
                                              disabled=st.session_state.editando_id is None)
        with col3:
            btn_excluir = st.form_submit_button("🗑️ Excluir", use_container_width=True,
                                              disabled=st.session_state.editando_id is None)
        with col4:
            btn_limpar = st.form_submit_button("🧹 Limpar", use_container_width=True)
    
    # PROCESSAR AÇÃO DO BOTÃO BUSCAR CEP (fora do form para evitar conflito)
    if 'btn_buscar_cep' in locals() and btn_buscar_cep:
        if cep:
            dados_cep = buscar_cep(cep)
            if dados_cep:
                st.session_state.form_data['endereco'] = dados_cep["endereco"]
                st.session_state.form_data['bairro'] = dados_cep["bairro"]
                st.session_state.form_data['cidade'] = dados_cep["cidade"]
                st.session_state.form_data['uf'] = dados_cep["uf"]
                st.rerun()
            else:
                st.error("CEP não encontrado!")
    
    # PROCESSAR AÇÕES (código mantido igual)
    if btn_incluir:
        if not nome.strip() or not cnpj_cpf.strip():
            st.error("❌ Campos Nome e CPF/CNPJ são obrigatórios!")
        else:
            dados = {
                "data_cad": data_cad.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "nome": nome.strip(),
                "data_nas": data_nas.strftime("%Y-%m-%d") if data_nas else None,
                "cnpj_cpf": re.sub(r'\D', '', cnpj_cpf),
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
                st.session_state.editando_id = None
                st.session_state.form_data = {
                    'data_cad': date.today(),
                    'tipo': 'Cliente',
                    'nome': '',
                    'data_nas': None,
                    'cnpj_cpf': '',
                    'cep': '',
                    'endereco': '',
                    'bairro': '',
                    'cidade': '',
                    'uf': '',
                    'telefone': '',
                    'email': '',
                    'obs': ''
                }
                st.rerun()
    
    if btn_alterar and st.session_state.editando_id:
        if not nome.strip() or not cnpj_cpf.strip():
            st.error("❌ Campos Nome e CPF/CNPJ são obrigatórios!")
        else:
            dados = {
                "data_cad": data_cad.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "nome": nome.strip(),
                "data_nas": data_nas.strftime("%Y-%m-%d") if data_nas else None,
                "cnpj_cpf": re.sub(r'\D', '', cnpj_cpf),
                "cep": re.sub(r'\D', '', cep) if cep else "",
                "endereco": endereco.strip(),
                "bairro": bairro.strip(),
                "cidade": cidade.strip(),
                "uf": uf.strip().upper(),
                "telefone": re.sub(r'\D', '', telefone) if telefone else "",
                "email": email.strip(),
                "obs": obs.strip()
            }
            
            if atualizar_relacionamento(dados, st.session_state.editando_id):
                st.rerun()
    
    if btn_excluir and st.session_state.editando_id:
        if excluir_relacionamento(st.session_state.editando_id):
            st.session_state.editando_id = None
            st.session_state.form_data = {
                'data_cad': date.today(),
                'tipo': 'Cliente',
                'nome': '',
                'data_nas': None,
                'cnpj_cpf': '',
                'cep': '',
                'endereco': '',
                'bairro': '',
                'cidade': '',
                'uf': '',
                'telefone': '',
                'email': '',
                'obs': ''
            }
            st.rerun()
    
    if btn_limpar:
        st.session_state.editando_id = None
        st.session_state.form_data = {
            'data_cad': date.today(),
            'tipo': 'Cliente',
            'nome': '',
            'data_nas': None,
            'cnpj_cpf': '',
            'cep': '',
            'endereco': '',
            'bairro': '',
            'cidade': '',
            'uf': '',
            'telefone': '',
            'email': '',
            'obs': ''
        }
        st.rerun()

# Função principal para ser chamada do main.py
def show():
    formulario_relacionamento()

# Para executar diretamente
if __name__ == "__main__":
    formulario_relacionamento()