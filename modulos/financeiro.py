import streamlit as st
import pandas as pd
import sqlite3
import base64
import logging
import os
import locale
import unicodedata
import sys
import importlib
from datetime import date, datetime
# No TOPO do arquivo:
from config import DB_FILE
import sqlite3

# Onde conecta ao banco:
conn = sqlite3.connect(DB_FILE)

if not os.path.exists(DB_FILE):
    raise FileNotFoundError(f"Banco de dados não encontrado em: {DB_FILE}")

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
# Funções auxiliares
# ----------------------------
def gerar_datas_parcelas(data_inicial, num_parcelas):
    from datetime import timedelta
    datas = []
    for i in range(num_parcelas):
        data_parcela = data_inicial + timedelta(days=30 * i)
        datas.append(data_parcela)
    return datas

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

# ----------------------------
# Banco de dados
# ----------------------------
def conectar_financeiro():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def carregar_financeiro(data_inicio=None, data_fim=None, categoria=None):
    """
    Carrega os registros financeiros do banco, com filtros opcionais:
    - data_inicio: datetime.date ou string 'YYYY-MM-DD'
    - data_fim: datetime.date ou string 'YYYY-MM-DD'
    - categoria: "Crédito" ou "Débito"
    
    Retorna um DataFrame pandas filtrado.
    """
    conn = conectar_financeiro()
    try:
        # Consulta base com WHERE dinâmico
        query = """
            SELECT rowid as id, data, tipo, grupo, subgrupo, plano, categoria, 
                   relacao, banco, descricao, valor, status 
            FROM financeiro 
            WHERE 1=1
        """
        params = []
        
        # Filtrar por datas, se fornecidas
        if data_inicio:
            if isinstance(data_inicio, str):
                data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            query += " AND data >= ?"
            params.append(data_inicio)
            
        if data_fim:
            if isinstance(data_fim, str):
                data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            query += " AND data <= ?"
            params.append(data_fim)
            
        # Filtrar por categoria, se fornecida - CORREÇÃO APLICADA
        if categoria and categoria.lower() in ["crédito", "débito", "credito", "debito"]:
            # Normalizar para buscar tanto com acento quanto sem
            cat_normalized = categoria.lower()
            if cat_normalized in ["crédito", "credito"]:
                query += " AND (LOWER(categoria) = 'crédito' OR LOWER(categoria) = 'credito')"
            elif cat_normalized in ["débito", "debito"]:
                query += " AND (LOWER(categoria) = 'débito' OR LOWER(categoria) = 'debito')"
        
        query += " ORDER BY data DESC"
        
        # Executar consulta com filtros
        df = pd.read_sql_query(query, conn, params=params)

        df = df.rename(columns={'id': 'rowid'})
        df = df.drop_duplicates(subset=['rowid'], keep='first')
        df = df.reset_index(drop=True)

        if not df.empty:
            # Converter coluna data para datetime.date
            df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
            
            # Ordenar por data decrescente
            df = df.sort_values("data", ascending=False)

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        df = pd.DataFrame(columns=["rowid", "data", "tipo", "grupo", "subgrupo", "plano", 
                                   "categoria", "relacao", "banco", "descricao", "valor", "status"])
    finally:
        conn.close()

    return df

def carregar_planos():
    conn = conectar_financeiro()
    try:
        df = pd.read_sql_query("SELECT * FROM plano", conn)
        for col in ["grupo", "subgrupo", "plano", "categoria"]:
            if col not in df.columns:
                df[col] = None
    except Exception as e:
        st.error(f"Erro ao carregar planos: {e}")
        df = pd.DataFrame(columns=["grupo", "subgrupo", "plano", "categoria"])
    finally:
        conn.close()
    return df

def carregar_relacionamentos():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT nome FROM relacionamento WHERE nome IS NOT NULL ORDER BY nome")
        relacionamentos = [row[0] for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Erro ao carregar relacionamentos: {e}")
        relacionamentos = []
    finally:
        conn.close()
    return relacionamentos

# ----------------------------
# CORREÇÃO: Função para carregar um registro completo
# ----------------------------
def carregar_registro_por_id(rowid):
    """Carrega um registro específico com todos os campos"""
    conn = conectar_financeiro()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rowid, * FROM financeiro 
            WHERE rowid = ?
        """, (int(rowid),))
        row = cursor.fetchone()
        if row:
            registro = dict(row)
            print(f"DEBUG - Registro carregado do banco: {registro}")
            return registro
        return None
    except Exception as e:
        st.error(f"Erro ao carregar registro: {e}")
        return None
    finally:
        conn.close()

# ----------------------------
# Operações CRUD
# ----------------------------
def salvar_registro(registro):
    campos = ["data", "tipo", "grupo", "subgrupo", "plano", "categoria", 
              "relacao", "banco", "descricao", "valor", "status"]
    conn = conectar_financeiro()
    try:
        placeholders = ", ".join(["?"] * len(campos))
        sql = f"INSERT INTO financeiro ({', '.join(campos)}) VALUES ({placeholders})"
        valores = [registro.get(campo, "") for campo in campos]
        cursor = conn.cursor()
        cursor.execute(sql, valores)
        conn.commit()
        if cursor.lastrowid:
            st.success(f"✅ Registro salvo com ID: {cursor.lastrowid}")
            return True
        else:
            st.error("❌ Falha ao salvar registro")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar registro: {e}")
        return False
    finally:
        conn.close()

def atualizar_registro(rowid, registro):
    campos = ["data", "tipo", "grupo", "subgrupo", "plano", "categoria", 
              "relacao", "banco", "descricao", "valor", "status"]
    conn = conectar_financeiro()
    try:
        rowid_int = int(rowid) if rowid else None
        if not rowid_int:
            st.error("❌ ID do registro inválido")
            return False
        sets = ", ".join([f"{campo}=?" for campo in campos])
        valores = [registro.get(campo, "") for campo in campos] + [rowid_int]
        sql = f"UPDATE financeiro SET {sets} WHERE rowid=?"
        cursor = conn.cursor()
        cursor.execute(sql, valores)
        conn.commit()
        if cursor.rowcount > 0:
            return True
        else:
            st.warning("⚠️ Nenhum registro foi atualizado")
            return False
    except Exception as e:
        st.error(f"Erro ao atualizar registro: {e}")
        return False
    finally:
        conn.close()

def excluir_registro(rowid):
    conn = conectar_financeiro()
    try:
        rowid_int = int(rowid) if rowid else None
        if not rowid_int:
            st.error("❌ ID do registro inválido")
            return False
        cursor = conn.cursor()
        cursor.execute("DELETE FROM financeiro WHERE rowid=?", (rowid_int,))
        conn.commit()
        if cursor.rowcount > 0:
            return True
        else:
            st.warning("⚠️ Nenhum registro foi excluído")
            return False
    except Exception as e:
        st.error(f"Erro ao excluir registro: {e}")
        return False
    finally:
        conn.close()

# ----------------------------
# Estado da sessão
# ----------------------------
def inicializar_estado_financeiro():
    if "financeiro_inicializado" not in st.session_state:
        estado_padrao = {
            "financeiro_inicializado": True,
            "financeiro_edit_rowid": None,
            "financeiro_tipo_selecionado": "Entrada",
            "financeiro_grupo_selecionado": "",
            "financeiro_subgrupo_selecionado": "",
            "financeiro_plano_selecionado": "",
            "financeiro_categoria": "Crédito",
            "financeiro_ultima_escolha": "",
            "financeiro_data": date.today(),
            "financeiro_valor": 0.0,
            "financeiro_status": "Aberto",
            "financeiro_banco": "",
            "financeiro_relacao": "",
            "financeiro_descricao": "",
            "financeiro_limpar_campos": False,
            "financeiro_acao_executada": False,
            "financeiro_data_inicio": date.today().replace(day=1),
            "financeiro_data_fim": date.today(),
            # Campos de transferência
            "transferencia_banco_debito": "",
            "transferencia_banco_credito": "",
            "transferencia_valor": 0.01,
            "transferencia_descricao": "Transferência entre contas"
        }
        for chave, valor in estado_padrao.items():
            if chave not in st.session_state:
                st.session_state[chave] = valor

def salvar_transferencia(banco_debito, banco_credito, valor, data_form, descricao="Transferência entre contas"):
    """
    Salva uma transferência como duas entradas no banco de dados:
    - Uma para débito (saída) do banco de origem
    - Uma para crédito (entrada) no banco de destino
    """
    # Registro de DÉBITO (saída do banco de origem)
    dados_debito = {
        "data": data_form.strftime("%Y-%m-%d") if isinstance(data_form, date) else data_form,
        "tipo": "Saída",
        "grupo": "Despesas",
        "subgrupo": "Transferências",
        "plano": "Bancos",
        "categoria": "Débito",
        "relacao": "Automático",
        "banco": banco_debito,
        "descricao": f"{descricao} - Saída: {banco_debito}",
        "valor": float(valor),
        "status": "Pago"
    }
    
    # Registro de CRÉDITO (entrada no banco de destino)
    dados_credito = {
        "data": data_form.strftime("%Y-%m-%d") if isinstance(data_form, date) else data_form,
        "tipo": "Entrada",
        "grupo": "Receitas",
        "subgrupo": "Transferências",
        "plano": "Bancos",
        "categoria": "Crédito",
        "relacao": "Automático",
        "banco": banco_credito,
        "descricao": f"{descricao} - Entrada: {banco_credito}",
        "valor": float(valor),
        "status": "Pago"
    }
    
    # Salva ambos os registros
    sucesso_debito = salvar_registro(dados_debito)
    sucesso_credito = salvar_registro(dados_credito)
    
    return sucesso_debito and sucesso_credito

# CORREÇÃO: Função limpar_campos_financeiro corrigida
def limpar_campos_financeiro():
    """Limpa todos os campos do formulário"""
    campos_limpos = {
        "financeiro_edit_rowid": None,
        "financeiro_ultima_escolha": "",
        "financeiro_data": date.today(),  # CORREÇÃO: Data atual
        "financeiro_valor": 0.0,          # CORREÇÃO: Valor zerado
        "financeiro_status": "Aberto",    # CORREÇÃO: Status padrão
        "financeiro_banco": "",           # CORREÇÃO: Banco vazio
        "financeiro_relacao": "",         # CORREÇÃO: Relação vazia
        "financeiro_descricao": "",       # CORREÇÃO: Descrição vazia
        "financeiro_grupo_selecionado": "",
        "financeiro_subgrupo_selecionado": "",
        "financeiro_plano_selecionado": "",
        "financeiro_limpar_campos": False,
        "financeiro_acao_executada": False,
        # Manter o tipo atual, mas resetar categoria
        "financeiro_categoria": "Crédito" if st.session_state.get("financeiro_tipo_selecionado", "Entrada") == "Entrada" else "Débito",
        # Limpar campos de transferência também
        "transferencia_banco_debito": "",
        "transferencia_banco_credito": "",
        "transferencia_valor": 0.01,
        "transferencia_descricao": "Transferência entre contas"
    }
    for campo, valor in campos_limpos.items():
        st.session_state[campo] = valor

# ----------------------------
# Interface principal
# ----------------------------
def exibir_financeiro():
    st.header("📊 Gestão Financeira")
    inicializar_estado_financeiro()

    # CORREÇÃO: Processar limpeza de campos ANTES de qualquer renderização
    if st.session_state.get("financeiro_limpar_campos", False):
        limpar_campos_financeiro()
        st.session_state["financeiro_limpar_campos"] = False
        st.rerun()

    # ----------------------------
    # Função de input de data BR
    # ----------------------------
    def date_input_br(label, key, value=None):
        """
        Campo de data brasileiro com calendário nativo.
        Retorna sempre uma data válida.
        """
        from datetime import datetime, date
        
        try:
            if value is None:
                value = st.session_state.get(key, date.today())
            
            # Garantir que value é um objeto date válido
            if isinstance(value, (datetime, pd.Timestamp)):
                value = value.date()
            elif isinstance(value, str):
                try:
                    value = datetime.strptime(value, "%Y-%m-%d").date()
                except:
                    try:
                        value = datetime.strptime(value, "%d/%m/%Y").date()
                    except:
                        value = date.today()
            elif not isinstance(value, date):
                value = date.today()
            
            # Define data mínima (01/01/1900)
            min_date = date(1900, 1, 1)
            
            # Usa o date_input nativo do Streamlit
            data_selecionada = st.date_input(
                label=label,
                value=value,
                min_value=min_date,
                max_value=None,
                format="DD/MM/YYYY",
                key=f"{key}_calendar"
            )
            
            # Atualiza o session_state
            st.session_state[key] = data_selecionada
            return data_selecionada
            
        except Exception as e:
            print(f"⚠️ DEBUG: Erro em date_input_br: {e}")
            # Fallback seguro
            fallback_date = date.today()
            st.session_state[key] = fallback_date
            return fallback_date

    # ----------------------------
    # Filtros de Data
    # ----------------------------
    styled_subheader("🔍 Filtros", "14px")
    col1, col2 = st.columns([1, 1])
    with col1:
        data_inicio = date_input_br("Data Inicial:", key="financeiro_data_inicio", value=date.today())
    with col2:
        data_fim = date_input_br("Data Final:", key="financeiro_data_fim", value=date.today())
    
    # VALIDAÇÃO CRÍTICA: Verificar se as datas são válidas antes de processar
    if data_inicio is None or data_fim is None:
        st.error("❌ Por favor, selecione datas válidas para continuar")
        st.stop()

    # ----------------------------
    # Carregar dados COM FILTROS APLICADOS - CORREÇÃO
    # ----------------------------
    # Aplicar filtro de categoria baseado no tipo selecionado
    categoria_filtro = None
    if st.session_state.get("financeiro_tipo_selecionado") == "Entrada":
        categoria_filtro = "Crédito"
    elif st.session_state.get("financeiro_tipo_selecionado") == "Saída":
        categoria_filtro = "Débito"

    df_fin = carregar_financeiro(
        data_inicio=data_inicio, 
        data_fim=data_fim, 
        categoria=categoria_filtro
    )
    
    df_planos = carregar_planos()
    opcoes = []

    # ----------------------------
    # Processamento de registros - CORREÇÃO COMPLETA
    # ----------------------------
    if not df_fin.empty:
        try:
            # Processar dados do dataframe
            df_fin["data"] = pd.to_datetime(df_fin["data"], errors="coerce").dt.date
            df_fin = df_fin.drop_duplicates(subset=['rowid'], keep='first')
            df_validas = df_fin[df_fin["data"].notnull()].copy()

            # Aplicar filtro de data (já aplicado na função, mas mantemos para segurança)
            mask = (df_validas["data"] >= data_inicio) & (df_validas["data"] <= data_fim)
            df_filtrado_periodo = df_validas.loc[mask].sort_values("data", ascending=False)

            # Resumo - CARREGAR DADOS COMPLETOS PARA O RESUMO
            df_fin_resumo = carregar_financeiro(data_inicio=data_inicio, data_fim=data_fim)
            total_credito = 0
            total_debito = 0
            saldo = 0
            
            if not df_fin_resumo.empty:
                df_fin_resumo["data"] = pd.to_datetime(df_fin_resumo["data"], errors="coerce").dt.date
                df_validas_resumo = df_fin_resumo[df_fin_resumo["data"].notnull()].copy()
                mask_resumo = (df_validas_resumo["data"] >= data_inicio) & (df_validas_resumo["data"] <= data_fim)
                df_resumo = df_validas_resumo.loc[mask_resumo].copy()
                df_resumo["valor"] = pd.to_numeric(df_resumo["valor"], errors="coerce").fillna(0)
                
                if "categoria" in df_resumo.columns:
                    total_credito = df_resumo.loc[df_resumo["categoria"].str.lower().isin(["crédito", "credito"]), "valor"].sum()
                    total_debito = df_resumo.loc[df_resumo["categoria"].str.lower().isin(["débito", "debito"]), "valor"].sum()
                
                saldo = total_credito - total_debito

            cor_saldo = "#008000" if saldo > 0 else "#CC0000" if saldo < 0 else "#555"

            # ----------------------------
            # Linha Resumo + Selectbox
            # ----------------------------
            col_resumo, col_select = st.columns([3, 8])
            with col_resumo:
                st.markdown(
                    f"""
                    <div style="
                        font-family: Calibri, sans-serif;
                        font-size: 7pt;
                        line-height: 1.2;
                        color: #222;
                        background-color: #f9f9f9;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 4px 8px;
                        margin-top: 4px;
                        margin-bottom: 6px;
                    ">
                        <b>Total de Créditos:</b> R$ {total_credito:,.2f}<br>
                        <b>Total de Débitos:</b> R$ {total_debito:,.2f}<br>
                        <b><span style="color:{cor_saldo}">Saldo no Período:</span></b> R$ {saldo:,.2f}
                    </div>
                    """.replace(",", "X").replace(".", ",").replace("X", "."),
                    unsafe_allow_html=True
                )

            with col_select:
                if not df_filtrado_periodo.empty:
                    for row in df_filtrado_periodo.itertuples():
                        rowid = getattr(row, "rowid", getattr(row, "Index", None))
                        data_val = getattr(row, "data", None)
                        descricao_val = getattr(row, "descricao", "Sem descrição")
                        valor_val = float(getattr(row, "valor", 0.0))
                        data_str = data_val.strftime("%d/%m/%Y") if isinstance(data_val, date) else str(data_val)
                        opcao = f"{rowid} - {data_str} - {(str(descricao_val) if descricao_val else 'Sem descrição')[:30]} (R$ {valor_val:.2f})"
                        opcoes.append(opcao)
                    
                    opcoes = list(dict.fromkeys(opcoes))  # Remove duplicatas
                    opcoes.sort(key=lambda x: datetime.strptime(x.split(" - ")[1], "%d/%m/%Y"), reverse=True)
                else:
                    st.info("ℹ️ Nenhum registro encontrado no período selecionado.")

                escolha = st.selectbox(
                    "Selecionar registro para edição:",
                    [""] + opcoes,
                    key="financeiro_selecao_registro"
                )

            # CORREÇÃO: Carregar dados COMPLETOS quando seleciona um registro
            if escolha and escolha != st.session_state.get("financeiro_ultima_escolha", ""):
                st.session_state["financeiro_ultima_escolha"] = escolha
                
                # Extrair o rowid da escolha
                rowid = escolha.split(" - ")[0].strip()
                
                # Carregar dados COMPLETOS do banco
                registro_completo = carregar_registro_por_id(rowid)
                
                if registro_completo:
                    # CORREÇÃO: Converter data corretamente
                    data_registro = registro_completo.get('data', date.today())
                    if isinstance(data_registro, str):
                        try:
                            data_registro = datetime.strptime(data_registro, "%Y-%m-%d").date()
                        except:
                            data_registro = date.today()
                    
                    # CORREÇÃO: Atualizar TODOS os campos do session_state
                    st.session_state.update({
                        "financeiro_edit_rowid": registro_completo.get('rowid', rowid),
                        "financeiro_data": data_registro,
                        "financeiro_valor": float(registro_completo.get('valor', 0.0)),
                        "financeiro_status": registro_completo.get('status', 'Aberto'),
                        "financeiro_banco": registro_completo.get('banco', ''),
                        "financeiro_descricao": registro_completo.get('descricao', ''),
                        "financeiro_grupo_selecionado": registro_completo.get('grupo', ''),
                        "financeiro_subgrupo_selecionado": registro_completo.get('subgrupo', ''),
                        "financeiro_plano_selecionado": registro_completo.get('plano', ''),
                        "financeiro_relacao": registro_completo.get('relacao', ''),
                        "financeiro_tipo_selecionado": registro_completo.get('tipo', 'Entrada'),
                        "financeiro_categoria": registro_completo.get('categoria', 'Crédito')
                    })
                    
                    # Forçar rerun para atualizar a interface
                    st.rerun()
                    
            elif not escolha and st.session_state.get("financeiro_ultima_escolha"):
                st.session_state["financeiro_ultima_escolha"] = ""
                st.session_state["financeiro_edit_rowid"] = None
                # CORREÇÃO: Limpar campos quando nenhum registro está selecionado
                st.session_state.update({
                    "financeiro_data": date.today(),
                    "financeiro_valor": 0.0,
                    "financeiro_status": "Aberto",
                    "financeiro_banco": "",
                    "financeiro_descricao": "",
                    "financeiro_grupo_selecionado": "",
                    "financeiro_subgrupo_selecionado": "",
                    "financeiro_plano_selecionado": "",
                    "financeiro_relacao": "",
                    "financeiro_tipo_selecionado": "Entrada",
                    "financeiro_categoria": "Crédito"
                })
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao processar registros: {e}")
            import traceback
            st.error(f"Detalhes: {traceback.format_exc()}")

    # ----------------------------
    # Tipo de transação (Entrada/Saída/Transferência)
    # ----------------------------
    col_tipo, _ = st.columns([2, 8])
    with col_tipo:
        tipo_anterior = st.session_state.get("financeiro_tipo_selecionado", "Entrada")
        tipo_selecionado = st.radio(
            "Tipo de Transação:",
            ["Entrada", "Saída", "Transferência"],
            index=0 if tipo_anterior == "Entrada" else 1 if tipo_anterior == "Saída" else 2,
            key="financeiro_tipo_radio"
        )
        
        # Atualizar categoria automaticamente quando o tipo muda
        if tipo_selecionado != tipo_anterior:
            st.session_state["financeiro_tipo_selecionado"] = tipo_selecionado
            # CORREÇÃO: Atualizar categoria baseada no tipo
            if tipo_selecionado == "Entrada":
                st.session_state["financeiro_categoria"] = "Crédito"
            elif tipo_selecionado == "Saída":
                st.session_state["financeiro_categoria"] = "Débito"
            st.rerun()

    # CORREÇÃO: Sincronizar categoria com o tipo atual
    tipo_atual = st.session_state["financeiro_tipo_selecionado"]
    if tipo_atual == "Entrada":
        st.session_state["financeiro_categoria"] = "Crédito"
    elif tipo_atual == "Saída":
        st.session_state["financeiro_categoria"] = "Débito"

    categoria = st.session_state["financeiro_categoria"]

    # ----------------------------
    # Filtrar planos para Classificação
    # ----------------------------
    if not df_planos.empty and "categoria" in df_planos.columns:
        df_planos["classificacao_norm"] = df_planos["categoria"].fillna("").apply(remover_acentos).str.lower()
        class_norm = remover_acentos(categoria).lower()
        df_filtrado = df_planos[df_planos["classificacao_norm"] == class_norm].copy()
    else:
        df_filtrado = df_planos.copy()

    for col in ["grupo", "subgrupo", "plano"]:
        if col in df_filtrado.columns:
            df_filtrado[col] = df_filtrado[col].fillna("").astype(str).str.strip()

    # ----------------------------
    # Classificação da Transação - CORREÇÃO
    # ----------------------------
    styled_subheader("📋 Classificação da Transação","14px")
    col1, col2, col3, col4, col5 = st.columns(5)

    # Grupo
    with col1:
        grupos = [""] + sorted(df_filtrado["grupo"].dropna().unique().tolist()) if not df_filtrado.empty else [""]
        grupo_selecionado = st.selectbox(
            "Grupo:",
            grupos,
            index=grupos.index(st.session_state.get("financeiro_grupo_selecionado", "")) if st.session_state.get("financeiro_grupo_selecionado", "") in grupos else 0,
            key="financeiro_grupo_select"
        )
        st.session_state["financeiro_grupo_selecionado"] = grupo_selecionado

    # Subgrupo
    with col2:
        subgrupos = [""] + sorted(df_filtrado[df_filtrado["grupo"] == grupo_selecionado]["subgrupo"].dropna().unique().tolist()) if grupo_selecionado and not df_filtrado.empty else [""]
        subgrupo_selecionado = st.selectbox(
            "Subgrupo:",
            subgrupos,
            index=subgrupos.index(st.session_state.get("financeiro_subgrupo_selecionado", "")) if st.session_state.get("financeiro_subgrupo_selecionado", "") in subgrupos else 0,
            disabled=len(subgrupos) == 1,
            key="financeiro_subgrupo_select"
        )
        st.session_state["financeiro_subgrupo_selecionado"] = subgrupo_selecionado

    # Plano
    with col3:
        planos_opcoes = [""] + sorted(df_filtrado[(df_filtrado["grupo"] == grupo_selecionado) & (df_filtrado["subgrupo"] == subgrupo_selecionado)]["plano"].dropna().unique().tolist()) if grupo_selecionado and subgrupo_selecionado and not df_filtrado.empty else [""]
        plano_selecionado = st.selectbox(
            "Plano:",
            planos_opcoes,
            index=planos_opcoes.index(st.session_state.get("financeiro_plano_selecionado", "")) if st.session_state.get("financeiro_plano_selecionado", "") in planos_opcoes else 0,
            disabled=len(planos_opcoes) == 1,
            key="financeiro_plano_select"
        )
        st.session_state["financeiro_plano_selecionado"] = plano_selecionado

    # Classificação Display - CORREÇÃO: Mostrar "Crédito" ou "Débito"
    with col4:
        # CORREÇÃO: Mostrar a categoria (Crédito/Débito) que será salva no banco
        categoria_display = st.session_state.get("financeiro_categoria", "Crédito")
        st.text_input("Classificação:", value=categoria_display, key="financeiro_categoria_display", disabled=True)

    # Relação
    with col5:
        relacionamentos = carregar_relacionamentos()
        relacao_selecionada = st.selectbox(
            "Relação:",
            [""] + relacionamentos,
            index=relacionamentos.index(st.session_state.get("financeiro_relacao", "")) + 1 if st.session_state.get("financeiro_relacao", "") in relacionamentos else 0,
            key="financeiro_relacao_select"
        )
        st.session_state["financeiro_relacao"] = relacao_selecionada

    # ----------------------------
    # Formulário principal - CORREÇÃO: Campos carregam valores do session_state
    # ----------------------------
    with st.form("form_financeiro", clear_on_submit=False):
        
        # SE FOR TRANSFERÊNCIA - Mostrar campos específicos
        if tipo_selecionado == "Transferência":
            styled_subheader("🔄 Transferência entre Contas", "14px")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                data_form = date_input_br("Data:*", "financeiro_data_form", st.session_state.get("financeiro_data", date.today()))
            
            with col2:
                bancos_brasileiros = [
                    "Banco do Brasil", "Bradesco", "Carteira", "Caixa Econômica", "Itaú",
                    "Inter", "Infinit Pay", "Mercado Pago", "Nubank", "PagBank", "PicPay", "Pan", "Pagaleve", "Revolut","Santander", "Toro"
                ]
                
                banco_debito = st.selectbox(
                    "Banco a Debitar:*",
                    options=[""] + bancos_brasileiros,
                    key="transferencia_banco_debito"
                )
            
            with col3:
                banco_credito = st.selectbox(
                    "Banco a Creditar:*",
                    options=[""] + bancos_brasileiros,
                    key="transferencia_banco_credito"
                )
            
            col4, col5 = st.columns(2)
            
            with col4:
                valor_form = st.number_input("Valor da Transferência:*", min_value=0.01, step=0.01, value=0.01, key="transferencia_valor")
            
            with col5:
                descricao_form = st.text_input("Descrição:", value="Transferência entre contas", key="transferencia_descricao")
            
            # Mostrar resumo da transferência
            if banco_debito and banco_credito and valor_form > 0:
                st.info(f"""
                **Resumo da Transferência:**
                - 💸 **Saída:** {banco_debito} → R$ {valor_form:.2f}
                - 💰 **Entrada:** {banco_credito} → R$ {valor_form:.2f}
                - 📅 **Data:** {data_form.strftime('%d/%m/%Y') if isinstance(data_form, date) else data_form}
                """)
        
        else:
            # FORMULÁRIO NORMAL (Entrada/Saída) - CORREÇÃO: Campos carregam valores do session_state
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 3, 2, 3, 5])

            # Data - CORREÇÃO: Carrega valor do session_state
            with col1:
                data_atual = st.session_state.get("financeiro_data", date.today())
                data_form = date_input_br("Data:*", "financeiro_data_form", data_atual)
            
            # Status - CORREÇÃO: Carrega valor do session_state
            with col2:
                status_atual = st.session_state.get("financeiro_status", "Aberto")
                status_form = st.selectbox("Status:", ["Aberto", "Pago"],
                                          index=0 if status_atual == "Aberto" else 1,
                                          key="financeiro_status_form")
            
            # Banco - CORREÇÃO: Carrega valor do session_state
            with col3:
                bancos_brasileiros = [
                    "Banco do Brasil", "Bradesco", "Carteira", "Caixa Econômica", "Itaú",
                    "Inter", "Infinit Pay", "Mercado Pago", "Nubank", "PagBank", "PicPay", "Pan", "Pagaleve", "Revolut","Santander", "Toro"
                ]
                
                banco_atual = st.session_state.get("financeiro_banco", "")
                opcoes_banco = [""] + bancos_brasileiros
                if banco_atual and banco_atual not in bancos_brasileiros:
                    opcoes_banco = [banco_atual, ""] + bancos_brasileiros
                
                banco_form = st.selectbox(
                    "Banco:",
                    options=opcoes_banco,
                    index=opcoes_banco.index(banco_atual) if banco_atual in opcoes_banco else 0,
                    key="financeiro_banco_form"
                )
            
            # Tipo de valor
            with col4:
                tipo_valor = st.radio("Tipo:", ["Único", "Parcelado"], horizontal=True, key="financeiro_tipo_valor")
            
            # Valor - CORREÇÃO: Carrega valor do session_state
            with col5:
                if tipo_valor == "Único":
                    valor_atual = st.session_state.get("financeiro_valor", 0.0)
                    valor_form = st.number_input("Valor:*", min_value=0.0, step=0.01,
                                                value=float(valor_atual),
                                                key="financeiro_valor_form")
                    st.session_state["financeiro_parcelamento"] = None
                else:
                    valor_total = st.number_input("Valor Total:*", min_value=0.0, step=0.01,
                                                 value=float(st.session_state.get("financeiro_valor_total", 0.0)),
                                                 key="financeiro_valor_total")
                    num_parcelas = st.selectbox("Parcelas:", options=list(range(1, 25)), index=0, key="financeiro_num_parcelas")
                    if valor_total > 0 and num_parcelas > 0:
                        valor_parcela_base = valor_total / num_parcelas
                        valor_primeiras_parcelas = round(valor_parcela_base, 2)
                        valor_ultima_parcela = round(valor_total - valor_primeiras_parcelas * (num_parcelas - 1), 2)
                        st.session_state["financeiro_parcelamento"] = {
                            "valor_total": valor_total,
                            "num_parcelas": num_parcelas,
                            "valor_parcelas": [valor_primeiras_parcelas] * (num_parcelas - 1) + [valor_ultima_parcela],
                            "tipo": "PARCELADO"
                        }
                        valor_form = valor_primeiras_parcelas
                        st.caption(f"**{num_parcelas}x** (1ª: R$ {valor_primeiras_parcelas:.2f}, Última: R$ {valor_ultima_parcela:.2f})")
                    else:
                        valor_form = 0.0
                        st.session_state["financeiro_parcelamento"] = None
            
            # Descrição - CORREÇÃO: Carrega valor do session_state - ✅ AJUSTE APLICADO
            with col6:
                descricao_atual = st.session_state.get("financeiro_descricao", "")
                descricao_form = st.text_input("Descrição:", 
                                              value=descricao_atual, 
                                              max_chars=40,  # ✅ Limite de 40 caracteres
                                              key="financeiro_descricao_form")

        st.caption("* Campos obrigatórios")

        # Botões
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1: btn_salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with col_btn2: btn_alterar = st.form_submit_button("✏️ Alterar", use_container_width=True)
        with col_btn3: btn_excluir = st.form_submit_button("🗑️ Excluir", use_container_width=True)
        with col_btn4: btn_limpar = st.form_submit_button("✖️ Limpar", use_container_width=True)

    # ----------------------------
    # Processamento de ações (Salvar/Alterar/Excluir/Limpar) - CORREÇÃO
    # ----------------------------
    acao_executada = False

    def validar_campos(dados):
        obrigatorios = ["data", "valor", "grupo", "subgrupo", "plano"]
        faltando = [campo for campo in obrigatorios if not dados.get(campo)]
        return faltando

    if btn_salvar:
        # SE FOR TRANSFERÊNCIA
        if tipo_selecionado == "Transferência":
            banco_debito = st.session_state.get("transferencia_banco_debito", "")
            banco_credito = st.session_state.get("transferencia_banco_credito", "")
            valor_transf = st.session_state.get("transferencia_valor", 0.0)
            descricao_transf = st.session_state.get("transferencia_descricao", "Transferência entre contas")
            
            # Validações
            if not banco_debito or not banco_credito:
                st.error("❌ Selecione os bancos de débito e crédito")
            elif banco_debito == banco_credito:
                st.error("❌ Os bancos de débito e crédito devem ser diferentes")
            elif valor_transf <= 0:
                st.error("❌ O valor da transferência deve ser maior que zero")
            else:
                if salvar_transferencia(banco_debito, banco_credito, valor_transf, data_form, descricao_transf):
                    st.success("✅ Transferência realizada com sucesso!")
                    st.session_state["financeiro_limpar_campos"] = True
                    acao_executada = True
        
        # SE FOR ENTRADA/SAÍDA NORMAL
        else:
            parcelamento_info = st.session_state.get("financeiro_parcelamento")
            if parcelamento_info and parcelamento_info["tipo"] == "PARCELADO":
                datas_parcelas = gerar_datas_parcelas(data_form, parcelamento_info["num_parcelas"])
                todas_salvas = True
                for i, (data_parcela, valor_parcela) in enumerate(zip(datas_parcelas, parcelamento_info["valor_parcelas"])):
                    dados = {
                        "data": data_parcela.strftime("%Y-%m-%d"),
                        "tipo": tipo_selecionado,
                        "grupo": st.session_state["financeiro_grupo_selecionado"],
                        "subgrupo": st.session_state["financeiro_subgrupo_selecionado"],
                        "plano": st.session_state["financeiro_plano_selecionado"],
                        "categoria": st.session_state["financeiro_categoria"],
                        "relacao": st.session_state["financeiro_relacao"],
                        "banco": banco_form,
                        "descricao": f"{descricao_form} - Parcela {i+1}/{parcelamento_info['num_parcelas']}",
                        "valor": float(valor_parcela),
                        "status": "Aberto"
                    }
                    faltando = validar_campos(dados)
                    if faltando:
                        st.error(f"❌ Campos obrigatórios faltando: {', '.join(faltando)}")
                        todas_salvas = False
                        break
                    if not salvar_registro(dados):
                        st.error(f"❌ Erro ao salvar parcela {i+1}")
                        todas_salvas = False
                        break
                if todas_salvas:
                    st.success(f"✅ {parcelamento_info['num_parcelas']} parcelas salvas com sucesso!")
                    st.session_state["financeiro_limpar_campos"] = True
                    st.session_state["financeiro_parcelamento"] = None
                    acao_executada = True
            else:
                dados = {
                    "data": data_form.strftime("%Y-%m-%d") if isinstance(data_form, date) else data_form,
                    "tipo": tipo_selecionado,
                    "grupo": st.session_state["financeiro_grupo_selecionado"],
                    "subgrupo": st.session_state["financeiro_subgrupo_selecionado"],
                    "plano": st.session_state["financeiro_plano_selecionado"],
                    "categoria": st.session_state["financeiro_categoria"],
                    "relacao": st.session_state["financeiro_relacao"],
                    "banco": banco_form,
                    "descricao": descricao_form,
                    "valor": float(valor_form),
                    "status": status_form
                }
                faltando = validar_campos(dados)
                if faltando:
                    st.error(f"❌ Campos obrigatórios faltando: {', '.join(faltando)}")
                else:
                    if salvar_registro(dados):
                        st.session_state["financeiro_limpar_campos"] = True
                        acao_executada = True

    elif btn_alterar:
        rowid = st.session_state.get("financeiro_edit_rowid")
        if not rowid:
            st.warning("⚠️ Selecione um registro para editar.")
        else:
            dados = {
                "data": data_form.strftime("%Y-%m-%d") if isinstance(data_form, date) else data_form,
                "tipo": tipo_selecionado,
                "grupo": st.session_state["financeiro_grupo_selecionado"],
                "subgrupo": st.session_state["financeiro_subgrupo_selecionado"],
                "plano": st.session_state["financeiro_plano_selecionado"],
                "categoria": st.session_state["financeiro_categoria"],
                "relacao": st.session_state["financeiro_relacao"],
                "banco": banco_form,
                "descricao": descricao_form,
                "valor": float(valor_form),
                "status": status_form
            }
            faltando = validar_campos(dados)
            if faltando:
                st.error(f"❌ Campos obrigatórios faltando: {', '.join(faltando)}")
            else:
                if atualizar_registro(rowid, dados):
                    st.session_state["financeiro_limpar_campos"] = True
                    acao_executada = True

    elif btn_excluir:
        rowid = st.session_state.get("financeiro_edit_rowid")
        if not rowid:
            st.warning("⚠️ Selecione um registro para excluir.")
        else:
            if excluir_registro(rowid):
                st.session_state["financeiro_limpar_campos"] = True
                acao_executada = True

    elif btn_limpar:
        # CORREÇÃO: Limpar campos imediatamente
        st.session_state["financeiro_limpar_campos"] = True
        acao_executada = True

    if acao_executada:
        st.rerun()

if __name__ == "__main__":
    exibir_financeiro()