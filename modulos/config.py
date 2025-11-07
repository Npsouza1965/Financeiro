# modulos/config.py
import os
import sys
import sqlite3

def resource_path(relative_path):
    """
    APENAS para recursos EMBUTIDOS no executável (imagens, ícones, CSS)
    """
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_path, relative_path)
    except Exception:
        return relative_path

# CORREÇÃO: Banco SEMPRE na MESMA pasta do executável
if getattr(sys, 'frozen', False):
    # MODO EXECUTÁVEL: Banco na pasta do .exe (qualquer máquina)
    DB_FILE = os.path.join(os.path.dirname(sys.executable), 'nps_financeiro.db')
    print(f"🎯 MODO EXECUTÁVEL - Banco criado junto com .exe")
else:
    # MODO DESENVOLVIMENTO: Banco no caminho fixo (sua máquina)
    DB_FILE = r"C:\NPS-FIN\dist\nps_financeiro.db"
    print(f"🔧 MODO DESENVOLVIMENTO - Banco no caminho fixo")

def criar_banco_se_nao_existir():
    """Cria o banco de dados e tabelas se não existirem"""
    if not os.path.exists(DB_FILE):
        print("📝 Criando banco de dados...")
        try:
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financeiro (
                    data TEXT, tipo TEXT, grupo TEXT, subgrupo TEXT,
                    plano TEXT, categoria TEXT, relacao TEXT, banco TEXT,
                    descricao TEXT, valor REAL, status TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plano (
                    grupo TEXT, subgrupo TEXT, plano TEXT, categoria TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relacionamento (
                    nome TEXT UNIQUE
                )
            """)
            
            conn.commit()
            conn.close()
            print("✅ Banco e tabelas criados com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao criar banco: {e}")
    else:
        print("✅ Banco já existe!")

# Inicializar
criar_banco_se_nao_existir()
print(f"📍 Banco: {DB_FILE}")