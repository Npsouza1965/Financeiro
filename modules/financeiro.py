import streamlit as st
import pandas as pd
import sqlite3
import base64
import os
import unicodedata
from datetime import date

# Configuração do banco de dados
DB_FILE = "financeiro.db"

# ----------------------------
# Funções de utilidade
# ----------------------------
def resource_path(relative_path):
    """Retorna o caminho correto para recursos"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def remover_acentos(texto):
    """Remove acentos do texto"""
    if not isinstance(texto, str):
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto) 
        if unicodedata.category(c) != 'Mn'
    )

# ----------------------------
# Conexão com banco de dados
# ----------------------------
def conectar_financeiro():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def carregar_financeiro():
    """Carrega dados financeiros do banco"""
    conn = conectar_financeiro()
    try:
        df = pd.read_sql_query("SELECT rowid, * FROM financeiro ORDER BY data DESC", conn)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        df = pd.DataFrame(columns=["rowid", "data", "tipo", "grupo", "subgrupo", "plano", 
                                 "classificacao", "entidade", "banco", "descricao", "valor", "status"])
    finally:
        conn.close()
    return df

def carregar_planos():
    """Carrega planos do banco"""
    conn = conectar_financeiro()
    try:
        df = pd.read_sql_query("SELECT * FROM Plano", conn)
        # Garante que as colunas necessárias existam
        for col in ["grupo", "subgrupo", "plano", "classificacao"]:
            if col not in df.columns:
                df[col] = None
    except Exception as e:
        st.error(f"Erro ao carregar planos: {e}")
        df = pd.DataFrame(columns=["grupo", "subgrupo", "plano", "classificacao"])
    finally:
        conn.close()
    return df

def carregar_entidades(tipo):
    """Carrega clientes ou fornecedores baseado no tipo"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        if tipo == "Entrada":
            cur.execute("SELECT DISTINCT nome FROM clientes WHERE nome IS NOT NULL ORDER BY nome")
        else:
            cur.execute("SELECT DISTINCT nome FROM fornecedores WHERE nome IS NOT NULL ORDER BY nome")
        entidades = [row[0] for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Erro ao carregar entidades: {e}")
        entidades = []
    finally:
        conn.close()
    return entidades

# ----------------------------
# Operações CRUD
# ----------------------------
def salvar_registro(registro):
    """Salva novo registro no banco"""
    campos = ["data", "tipo", "grupo", "subgrupo", "plano", "classificacao", 
              "entidade", "banco", "descricao", "valor", "status"]
    
    conn = conectar_financeiro()
    try:
        placeholders = ", ".join(["?"] * len(campos))
        conn.execute(
            f"INSERT INTO financeiro ({', '.join(campos)}) VALUES ({placeholders})",
            [registro.get(campo, "") for campo in campos]
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar registro: {e}")
        return False
    finally:
        conn.close()

def atualizar_registro(rowid, registro):
    """Atualiza registro existente"""
    campos = ["data", "tipo", "grupo", "subgrupo", "plano", "classificacao", 
              "entidade", "banco", "descricao", "valor", "status"]
    
    conn = conectar_financeiro()
    try:
        sets = ", ".join([f"{campo}=?" for campo in campos])
        valores = [registro.get(campo, "") for campo in campos]
        valores.append(rowid)
        
        conn.execute(f"UPDATE financeiro SET {sets} WHERE rowid=?", valores)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar registro: {e}")
        return False
    finally:
        conn.close()

def excluir_registro(rowid):
    """Exclui registro do banco"""
    conn = conectar_financeiro()
    try:
        conn.execute("DELETE FROM financeiro WHERE rowid=?", (rowid,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir registro: {e}")
        return False
    finally:
        conn.close()

# ----------------------------
# Inicialização do estado
# ----------------------------
def inicializar_estado_financeiro():
    """Inicializa o estado da sessão para o módulo financeiro"""
    if "financeiro_inicializado" not in st.session_state:
        estado_padrao = {
            "financeiro_inicializado": True,
            "financeiro_edit_rowid": None,
            "financeiro_tipo_selecionado": "Entrada",
            "financeiro_grupo_selecionado": "",
            "financeiro_subgrupo_selecionado": "",
            "financeiro_plano_selecionado": "",
            "financeiro_classificacao": "Crédito",
            "financeiro_ultima_escolha": "",
            "financeiro_data": date.today(),
            "financeiro_valor": 0.0,
            "financeiro_status": "Aberto",
            "financeiro_banco": "",
            "financeiro_entidade": "",
            "financeiro_descricao": "",
            "financeiro_limpar_campos": False,
            "financeiro_acao_executada": False  # CORREÇÃO: Nova flag para controle
        }
        
        for chave, valor in estado_padrao.items():
            st.session_state[chave] = valor

def limpar_campos_financeiro():
    """Limpa todos os campos do formulário financeiro"""
    campos_para_limpar = [
        "financeiro_edit_rowid", "financeiro_ultima_escolha", 
        "financeiro_data", "financeiro_valor", "financeiro_status", 
        "financeiro_banco", "financeiro_entidade", "financeiro_descricao",
        "financeiro_grupo_selecionado", "financeiro_subgrupo_selecionado", 
        "financeiro_plano_selecionado", "financeiro_limpar_campos",
        "financeiro_acao_executada"
    ]
    
    for campo in campos_para_limpar:
        if campo == "financeiro_data":
            st.session_state[campo] = date.today()
        elif campo == "financeiro_valor":
            st.session_state[campo] = 0.0
        elif campo == "financeiro_status":
            st.session_state[campo] = "Aberto"
        elif campo == "financeiro_limpar_campos" or campo == "financeiro_acao_executada":
            st.session_state[campo] = False
        else:
            st.session_state[campo] = ""

# ----------------------------
# Interface principal
# ----------------------------
def exibir_financeiro():
    st.header("📊 Gestão Financeira")
    
    # Inicialização do estado
    inicializar_estado_financeiro()
    
    # CORREÇÃO: Verificar se precisa limpar campos após ação
    if st.session_state.get("financeiro_limpar_campos", False):
        limpar_campos_financeiro()
        # Não usar st.rerun() aqui - causa o erro removeChild
    
    # Filtros de período
    st.subheader("🔍 Filtros")
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data inicial:", value=date.today(), key="financeiro_data_inicio")
    with col2:
        data_fim = st.date_input("Data final:", value=date.today(), key="financeiro_data_fim")

    # Carregar dados
    df_fin = carregar_financeiro()
    df_planos = carregar_planos()

    # Controles principais
    st.subheader("📝 Nova Transação")
    
    # Seleção do tipo
    col1, col2 = st.columns([2, 1])
    with col1:
        tipo_anterior = st.session_state["financeiro_tipo_selecionado"]
        tipo_selecionado = st.radio(
            "Tipo de transação:",
            ["Entrada", "Saída"],
            index=0 if st.session_state["financeiro_tipo_selecionado"] == "Entrada" else 1,
            key="financeiro_tipo_radio"
        )
        
        # Atualizar estado se o tipo mudou
        if tipo_selecionado != tipo_anterior:
            st.session_state["financeiro_tipo_selecionado"] = tipo_selecionado
            st.session_state["financeiro_classificacao"] = "Crédito" if tipo_selecionado == "Entrada" else "Débito"
            st.session_state["financeiro_grupo_selecionado"] = ""
            st.session_state["financeiro_subgrupo_selecionado"] = ""
            st.session_state["financeiro_plano_selecionado"] = ""
            st.session_state["financeiro_entidade"] = ""
            # CORREÇÃO: Não usar st.rerun() - atualiza automaticamente no próximo render
    
    with col2:
        if st.button("🔄 Limpar Filtros", use_container_width=True, key="financeiro_limpar_filtros"):
            st.session_state["financeiro_grupo_selecionado"] = ""
            st.session_state["financeiro_subgrupo_selecionado"] = ""
            st.session_state["financeiro_plano_selecionado"] = ""
            st.session_state["financeiro_entidade"] = ""
            # CORREÇÃO: Não usar st.rerun()

    # Classificação automática baseada no tipo
    classificacao = "Crédito" if tipo_selecionado == "Entrada" else "Débito"
    st.session_state["financeiro_classificacao"] = classificacao
    
    # Filtrar planos pela classificação
    if not df_planos.empty and "classificacao" in df_planos.columns:
        df_planos["classificacao_norm"] = df_planos["classificacao"].fillna("").apply(remover_acentos).str.lower()
        class_norm = remover_acentos(classificacao).lower()
        df_filtrado = df_planos[df_planos["classificacao_norm"] == class_norm].copy()
    else:
        df_filtrado = df_planos.copy()

    # Limpeza das colunas
    for col in ["grupo", "subgrupo", "plano"]:
        if col in df_filtrado.columns:
            df_filtrado[col] = df_filtrado[col].fillna("").astype(str).str.strip()

    # Seleção de registro existente para edição
    registro_selecionado = None
    if not df_fin.empty:
        df_fin["data"] = pd.to_datetime(df_fin["data"], errors="coerce")
        df_filtrado_periodo = df_fin[
            (df_fin["data"] >= pd.to_datetime(data_inicio)) &
            (df_fin["data"] <= pd.to_datetime(data_fim)) &
            (df_fin["tipo"] == tipo_selecionado)
        ].sort_values("data", ascending=False)
        
        if not df_filtrado_periodo.empty:
            opcoes = [
                f"{row['rowid']} - {row['data'].strftime('%d/%m/%Y')} - {row.get('descricao', '')} (R$ {float(row.get('valor', 0)):.2f})"
                for _, row in df_filtrado_periodo.iterrows()
            ]
            
            escolha = st.selectbox("Selecionar registro para edição:", [""] + opcoes, key="financeiro_selecao_registro")
            
            # Preencher automaticamente quando um registro é selecionado
            if escolha and escolha != st.session_state["financeiro_ultima_escolha"]:
                st.session_state["financeiro_ultima_escolha"] = escolha
                rowid = int(escolha.split(" - ")[0])
                registro_selecionado = df_filtrado_periodo[df_filtrado_periodo["rowid"] == rowid].iloc[0]
                st.session_state["financeiro_edit_rowid"] = rowid
                
                # Preencher TODOS os campos com dados do registro selecionado
                st.session_state["financeiro_data"] = registro_selecionado["data"].date() if hasattr(registro_selecionado["data"], 'date') else date.today()
                st.session_state["financeiro_valor"] = float(registro_selecionado.get("valor", 0))
                st.session_state["financeiro_status"] = registro_selecionado.get("status", "Aberto")
                st.session_state["financeiro_banco"] = registro_selecionado.get("banco", "")
                st.session_state["financeiro_descricao"] = registro_selecionado.get("descricao", "")
                st.session_state["financeiro_grupo_selecionado"] = registro_selecionado.get("grupo", "")
                st.session_state["financeiro_subgrupo_selecionado"] = registro_selecionado.get("subgrupo", "")
                st.session_state["financeiro_plano_selecionado"] = registro_selecionado.get("plano", "")
                st.session_state["financeiro_entidade"] = registro_selecionado.get("entidade", "")
                st.session_state["financeiro_classificacao"] = registro_selecionado.get("classificacao", classificacao)
                
                # CORREÇÃO: Não usar st.rerun() - marca flag para limpeza posterior
                st.session_state["financeiro_acao_executada"] = True
            elif not escolha:
                st.session_state["financeiro_ultima_escolha"] = ""
                st.session_state["financeiro_edit_rowid"] = None
        else:
            st.session_state["financeiro_edit_rowid"] = None

    # Formulário de classificação
    st.subheader("📋 Classificação da Transação")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Grupo
    with col1:
        grupos = [""] + sorted(df_filtrado["grupo"].dropna().unique().tolist()) if not df_filtrado.empty else [""]
        grupo_selecionado = st.selectbox(
            "Grupo:",
            grupos,
            index=grupos.index(st.session_state["financeiro_grupo_selecionado"]) if st.session_state["financeiro_grupo_selecionado"] in grupos else 0,
            key="financeiro_grupo_select"
        )
        st.session_state["financeiro_grupo_selecionado"] = grupo_selecionado

    # Subgrupo
    with col2:
        subgrupos = [""]
        if grupo_selecionado and not df_filtrado.empty:
            subgrupos_filtrados = df_filtrado[df_filtrado["grupo"] == grupo_selecionado]["subgrupo"].dropna().unique()
            subgrupos = [""] + sorted(subgrupos_filtrados.tolist())
        
        subgrupo_selecionado = st.selectbox(
            "Subgrupo:",
            subgrupos,
            index=subgrupos.index(st.session_state["financeiro_subgrupo_selecionado"]) if st.session_state["financeiro_subgrupo_selecionado"] in subgrupos else 0,
            disabled=len(subgrupos) == 1,
            key="financeiro_subgrupo_select"
        )
        st.session_state["financeiro_subgrupo_selecionado"] = subgrupo_selecionado

    # Plano
    with col3:
        planos_opcoes = [""]
        if grupo_selecionado and subgrupo_selecionado and not df_filtrado.empty:
            planos_filtrados = df_filtrado[
                (df_filtrado["grupo"] == grupo_selecionado) & 
                (df_filtrado["subgrupo"] == subgrupo_selecionado)
            ]["plano"].dropna().unique()
            planos_opcoes = [""] + sorted(planos_filtrados.tolist())
        
        plano_selecionado = st.selectbox(
            "Plano:",
            planos_opcoes,
            index=planos_opcoes.index(st.session_state["financeiro_plano_selecionado"]) if st.session_state["financeiro_plano_selecionado"] in planos_opcoes else 0,
            disabled=len(planos_opcoes) == 1,
            key="financeiro_plano_select"
        )
        st.session_state["financeiro_plano_selecionado"] = plano_selecionado

    # Classificação (somente leitura)
    with col4:
        classificacao_display = st.text_input(
            "Classificação:",
            value=st.session_state["financeiro_classificacao"],
            key="financeiro_classificacao_display",
            disabled=True
        )

    # Entidade
    with col5:
        entidades = carregar_entidades(tipo_selecionado)
        entidade_selecionada = st.selectbox(
            "Entidade:",
            [""] + entidades,
            index=entidades.index(st.session_state["financeiro_entidade"]) + 1 if st.session_state["financeiro_entidade"] in entidades else 0,
            key="financeiro_entidade_select"
        )
        st.session_state["financeiro_entidade"] = entidade_selecionada

    # Formulário principal
    with st.form("form_financeiro"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            data = st.date_input("Data:*", value=st.session_state["financeiro_data"], key="financeiro_data_form")
        with col2:
            valor = st.number_input("Valor:*", min_value=0.0, step=0.01, value=st.session_state["financeiro_valor"], key="financeiro_valor_form")
        with col3:
            status = st.selectbox("Status:", ["Aberto", "Pago"], 
                                index=0 if st.session_state["financeiro_status"] == "Aberto" else 1, 
                                key="financeiro_status_form")
        with col4:
            banco = st.text_input("Banco:", value=st.session_state["financeiro_banco"], key="financeiro_banco_form")
        
        descricao = st.text_area("Descrição:", value=st.session_state["financeiro_descricao"], height=60, key="financeiro_descricao_form")
        
        st.caption("* Campos obrigatórios")
        
        # Botões de ação
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1:
            btn_salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with col_btn2:
            btn_alterar = st.form_submit_button("✏️ Alterar", use_container_width=True)
        with col_btn3:
            btn_excluir = st.form_submit_button("🗑️ Excluir", use_container_width=True)
        with col_btn4:
            btn_limpar = st.form_submit_button("✖️ Limpar", use_container_width=True)

    # Processamento das ações (FORA do formulário)
    if btn_salvar or btn_alterar or btn_excluir or btn_limpar:
        # Preparar dados
        dados_transacao = {
            "data": data,
            "tipo": tipo_selecionado,
            "grupo": st.session_state["financeiro_grupo_selecionado"],
            "subgrupo": st.session_state["financeiro_subgrupo_selecionado"],
            "plano": st.session_state["financeiro_plano_selecionado"],
            "classificacao": st.session_state["financeiro_classificacao"],
            "entidade": st.session_state["financeiro_entidade"],
            "banco": banco,
            "descricao": descricao,
            "valor": valor,
            "status": status
        }
        
        # Validar campos obrigatórios
        campos_obrigatorios = ["data", "valor", "grupo", "subgrupo", "plano"]
        campos_faltantes = [campo for campo in campos_obrigatorios if not dados_transacao[campo]]
        
        if btn_salvar:
            if campos_faltantes:
                st.error(f"❌ Campos obrigatórios faltando: {', '.join(campos_faltantes)}")
            else:
                # Novo registro
                if salvar_registro(dados_transacao):
                    st.success("✅ Registro salvo com sucesso!")
                    st.session_state["financeiro_limpar_campos"] = True
        
        elif btn_alterar:
            if st.session_state["financeiro_edit_rowid"]:
                if campos_faltantes:
                    st.error(f"❌ Campos obrigatórios faltando: {', '.join(campos_faltantes)}")
                else:
                    # Editar registro
                    if atualizar_registro(st.session_state["financeiro_edit_rowid"], dados_transacao):
                        st.success("✅ Registro atualizado com sucesso!")
                        st.session_state["financeiro_limpar_campos"] = True
            else:
                st.warning("⚠️ Selecione um registro para editar.")
        
        elif btn_excluir:
            if st.session_state["financeiro_edit_rowid"]:
                if excluir_registro(st.session_state["financeiro_edit_rowid"]):
                    st.success("✅ Registro excluído com sucesso!")
                    st.session_state["financeiro_limpar_campos"] = True
            else:
                st.warning("⚠️ Selecione um registro para excluir.")
        
        elif btn_limpar:
            st.session_state["financeiro_limpar_campos"] = True
            st.success("🔄 Formulário limpo!")

if __name__ == "__main__":
    exibir_financeiro()