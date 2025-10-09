import streamlit as st
import sqlite3
import re
import requests
import logging
from validate_docbr import CNPJ, CPF

# ----------------------------
# Funções de formatação
# ----------------------------

def formatar_cep(valor: str) -> str:
    """Formata CEP no padrão 00000-000"""
    if not valor:
        return ""
    numeros = re.sub(r"\D", "", valor)
    if len(numeros) == 8:
        return f"{numeros[:5]}-{numeros[5:8]}"
    return numeros

def somente_digitos(texto: str) -> str:
    """Remove tudo que não for dígito"""
    return re.sub(r'\D', '', texto or '')

def formatar_cpf(cpf: str) -> str:
    """Formata CPF no padrão 000.000.000-00"""
    digitos = somente_digitos(cpf)
    if len(digitos) != 11:
        return digitos
    return f"{digitos[0:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"

def validar_cpf(cpf: str) -> bool:
    """Valida CPF verificando dígitos verificadores"""
    d = somente_digitos(cpf)
    if len(d) != 11:
        return False

    # Elimina CPFs com todos os dígitos iguais
    if d == d[0] * 11:
        return False

    # Converte para lista de inteiros
    nums = [int(ch) for ch in d]

    # Cálculo do primeiro dígito verificador
    s1 = sum((10 - i) * nums[i] for i in range(9))
    r1 = (s1 * 10) % 11
    if r1 == 10:
        r1 = 0
    if r1 != nums[9]:
        return False

    # Cálculo do segundo dígito verificador
    s2 = sum((11 - i) * nums[i] for i in range(10))
    r2 = (s2 * 10) % 11
    if r2 == 10:
        r2 = 0
    if r2 != nums[10]:
        return False

    return True

def formatar_telefone(valor: str) -> str:
    """Formata telefone no padrão (00) 00000-0000"""
    if not valor:
        return ""
    numeros = re.sub(r"\D", "", valor)
    if len(numeros) == 11:  # Celular com DDD
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:11]}"
    elif len(numeros) == 10:  # Fixo com DDD
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:10]}"
    elif len(numeros) > 2:
        return f"({numeros[:2]}) {numeros[2:]}"
    return numeros

def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ usando a biblioteca validate_docbr"""
    cnpj_obj = CNPJ()
    cnpj_limpo = somente_digitos(cnpj)
    return cnpj_obj.validate(cnpj_limpo)

def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ no padrão 00.000.000/0000-00"""
    cnpj = somente_digitos(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

def limpar_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ, deixando apenas números"""
    return somente_digitos(cnpj)

# ----------------------------
# Busca de endereço por CEP
# ----------------------------

def buscar_endereco_por_cep(cep: str):
    """
    Busca endereço no ViaCEP a partir de um CEP.
    Retorna um dicionário com endereco, bairro, cidade e uf.
    """
    try:
        cep = somente_digitos(cep)
        if len(cep) != 8:
            return None

        url = f"https://viacep.com.br/ws/{cep}/json/"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "erro" not in data:
                return {
                    "Endereco": data.get("logradouro", ""),
                    "Bairro": data.get("bairro", ""),
                    "Cidade": data.get("localidade", ""),
                    "UF": data.get("uf", "")
                }
    except Exception as e:
        logging.error(f"Erro ao buscar CEP: {e}")
        st.error(f"Erro ao buscar CEP: {e}")

    return None

# ----------------------------
# Busca de fornecedor pelo CNPJ
# ----------------------------

def buscar_dados_cnpj(cnpj: str, db_file: str = "financeiro.db"):
    """
    Busca dados de fornecedor pelo CNPJ no banco de dados
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, cnpj, nome, cep, endereco, cidade, bairro, UF, telefone, email, observacoes
            FROM fornecedores
            WHERE cnpj=?
        """, (cnpj.strip(),))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            return {
                "id": resultado[0],
                "cnpj": resultado[1],
                "nome": resultado[2],
                "cep": resultado[3],
                "endereco": resultado[4],
                "cidade": resultado[5],
                "bairro": resultado[6],
                "UF": resultado[7],
                "telefone": resultado[8],
                "email": resultado[9],
                "observacoes": resultado[10]
            }
    except Exception as e:
        logging.error(f"Erro ao buscar CNPJ no banco: {e}")
        st.error(f"Erro ao buscar dados: {e}")
    
    return None

# ----------------------------
# Widgets do Streamlit com formatação automática
# ----------------------------

def widget_cep(label: str, key: str, value: str = ""):
    """Widget de CEP com formatação automática"""
    def formatar_cep_callback():
        st.session_state[key] = formatar_cep(st.session_state[key])
    
    return st.text_input(
        label,
        value=value,
        key=key,
        on_change=formatar_cep_callback,
        max_chars=9
    )

def widget_cpf(label: str, key: str, value: str = ""):
    """Widget de CPF com formatação automática"""
    def formatar_cpf_callback():
        st.session_state[key] = formatar_cpf(st.session_state[key])
    
    cpf = st.text_input(
        label,
        value=value,
        key=key,
        on_change=formatar_cpf_callback,
        max_chars=14
    )
    
    # Validação em tempo real
    if cpf and len(somente_digitos(cpf)) == 11:
        if not validar_cpf(cpf):
            st.error("CPF inválido")
    
    return cpf

def widget_cnpj(label: str, key: str, value: str = ""):
    """Widget de CNPJ com formatação automática"""
    def formatar_cnpj_callback():
        st.session_state[key] = formatar_cnpj(st.session_state[key])
    
    cnpj = st.text_input(
        label,
        value=value,
        key=key,
        on_change=formatar_cnpj_callback,
        max_chars=18
    )
    
    # Validação em tempo real
    if cnpj and len(somente_digitos(cnpj)) == 14:
        if not validar_cnpj(cnpj):
            st.error("CNPJ inválido")
    
    return cnpj

def widget_telefone(label: str, key: str, value: str = ""):
    """Widget de telefone com formatação automática"""
    def formatar_telefone_callback():
        st.session_state[key] = formatar_telefone(st.session_state[key])
    
    return st.text_input(
        label,
        value=value,
        key=key,
        on_change=formatar_telefone_callback,
        max_chars=15
    )

# ----------------------------
# Testes (executado apenas quando o arquivo é rodado diretamente)
# ----------------------------

if __name__ == "__main__":
    st.title("🧪 Teste de Formatação")
    
    st.subheader("CPF")
    cpf_test = widget_cpf("Digite um CPF:", "test_cpf")
    if cpf_test:
        st.write(f"CPF válido: {validar_cpf(cpf_test)}")
    
    st.subheader("CNPJ")
    cnpj_test = widget_cnpj("Digite um CNPJ:", "test_cnpj")
    if cnpj_test:
        st.write(f"CNPJ válido: {validar_cnpj(cnpj_test)}")
    
    st.subheader("CEP")
    cep_test = widget_cep("Digite um CEP:", "test_cep")
    if cep_test and len(somente_digitos(cep_test)) == 8:
        endereco = buscar_endereco_por_cep(cep_test)
        if endereco:
            st.json(endereco)
    
    st.subheader("Telefone")
    tel_test = widget_telefone("Digite um telefone:", "test_tel")