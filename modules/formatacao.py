import re
import requests

# ==========================================================
# CPF
# ==========================================================

def validar_cpf(cpf: str) -> bool:
    """
    Valida um CPF (com ou sem pontuação).
    Retorna True se o CPF for válido.
    """
    if not cpf:
        return False

    # Remove tudo que não for número
    cpf = re.sub(r'\D', '', cpf)

    # CPF deve ter 11 dígitos
    if len(cpf) != 11:
        return False

    # Descarta CPFs com todos os dígitos iguais
    if cpf == cpf[0] * 11:
        return False

    # Validação matemática
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return cpf[-2:] == f"{digito1}{digito2}"


def formatar_cpf(cpf: str) -> str:
    """
    Retorna o CPF formatado no padrão 000.000.000-00.
    """
    if not cpf:
        return ""
    cpf = re.sub(r'\D', '', cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf


# ==========================================================
# CEP
# ==========================================================

def formatar_cep(cep: str) -> str:
    """
    Retorna o CEP formatado no padrão 00000-000.
    """
    if not cep:
        return ""
    cep = re.sub(r'\D', '', cep)
    return f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else cep


def buscar_endereco_por_cep(cep: str) -> dict:
    """
    Busca endereço a partir de um CEP usando a API ViaCEP.
    Retorna dicionário com Endereco, Bairro, Cidade e UF.
    """
    if not cep:
        return {}

    cep = re.sub(r'\D', '', cep)
    if len(cep) != 8:
        return {}

    url = f"https://viacep.com.br/ws/{cep}/json/"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "erro" in data:
            return {}

        return {
            "Endereco": data.get("logradouro", ""),
            "Bairro": data.get("bairro", ""),
            "Cidade": data.get("localidade", ""),
            "UF": data.get("uf", "")
        }

    except requests.RequestException:
        # Evita quebra por erro de rede
        return {}


# ==========================================================
# TELEFONE
# ==========================================================

def formatar_telefone(telefone: str) -> str:
    """
    Retorna o telefone formatado:
      - (00) 00000-0000 para 11 dígitos
      - (00) 0000-0000  para 10 dígitos
    """
    if not telefone:
        return ""
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone
# ==========================================================
# CNPJ
# ==========================================================

def validar_cnpj(cnpj: str) -> bool:
    """
    Valida um CNPJ com ou sem formatação.
    Retorna True se o CNPJ for válido.
    """
    if not cnpj:
        return False

    # Remove tudo que não for número
    cnpj = re.sub(r'\D', '', cnpj)

    # CNPJ deve ter 14 dígitos
    if len(cnpj) != 14:
        return False

    # Descarta CNPJs com todos os dígitos iguais
    if cnpj == cnpj[0] * 14:
        return False

    # Cálculo do primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    # Cálculo do segundo dígito verificador
    pesos2 = [6] + pesos1
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return cnpj[-2:] == f"{digito1}{digito2}"


def formatar_cnpj(cnpj: str) -> str:
    """
    Formata o CNPJ no padrão 00.000.000/0000-00
    """
    if not cnpj:
        return ""
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


# =====================
# Teste rápido
# =====================
if __name__ == "__main__":
    cnpjs = ["12.345.678/0001-95", "11222333000181", "00.000.000/0000-00"]
    for c in cnpjs:
        print(f"CNPJ: {c} | Válido? {validar_cnpj(c)} | Formatado: {formatar_cnpj(c)}")

# ==========================================================
# TESTE LOCAL (opcional)
# ==========================================================
if __name__ == "__main__":
    print("CPF válido?", validar_cpf("390.533.447-05"))
    print("CPF formatado:", formatar_cpf("39053344705"))
    print("CEP formatado:", formatar_cep("88010301"))
    print("Telefone formatado:", formatar_telefone("48999998888"))
    print("Endereço ViaCEP:", buscar_endereco_por_cep("88010301"))
