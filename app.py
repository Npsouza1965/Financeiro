# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import webbrowser
import socket
import time
import shutil

# ============================================
# Sistema Financeiro Hórus - Launcher para pasta dist
# ============================================

def check_dependencies():
    """Verifica dependências sem tentar instalar"""
    print("🔧 Verificando dependências...")
    
    dependencies = [
        ('streamlit', 'streamlit'),
        ('pandas', 'pandas'), 
        ('numpy', 'numpy'),
        ('matplotlib', 'matplotlib.pyplot'),
        ('plotly', 'plotly'),
        ('reportlab', 'reportlab.pdfgen'),
        ('fpdf', 'fpdf')
    ]
    
    missing_deps = []
    
    for package_name, import_name in dependencies:
        try:
            if import_name == 'fpdf':
                # Tenta ambos fpdf e fpdf2
                try:
                    __import__('fpdf')
                except ImportError:
                    __import__('fpdf2')
            else:
                __import__(import_name.split('.')[0])
            print(f"   ✅ {package_name}")
        except ImportError:
            missing_deps.append(package_name)
            print(f"   ❌ {package_name}")
    
    if missing_deps:
        print(f"\n❌ Dependências faltantes: {', '.join(missing_deps)}")
        print("\n💡 SOLUÇÃO:")
        print("   pip install streamlit pandas numpy matplotlib plotly reportlab fpdf2")
        return False
    
    print("✅ Todas as dependências OK!")
    return True

def find_main_path():
    """Localiza o main.py"""
    possible_paths = [
        os.path.join('modulos', 'main.py'),
        'main.py',
        os.path.join('src', 'modulos', 'main.py'),
        os.path.join('.', 'modulos', 'main.py'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Main encontrado: {path}")
            return path
    
    print("❌ main.py não encontrado.")
    return None

def find_or_create_db():
    """Localiza ou cria banco de dados na pasta dist/ - CORRIGIDO"""
    # Caminho para a pasta dist
    dist_path = 'dist'
    db_path = os.path.join(dist_path, 'nps_financeiro.db')
    
    # Criar pasta dist se não existir
    if not os.path.exists(dist_path):
        print(f"📁 Criando pasta: {dist_path}")
        os.makedirs(dist_path, exist_ok=True)
    
    if os.path.exists(db_path):
        print(f"✅ Banco de dados encontrado: {db_path}")
        return db_path
    else:
        print(f"⚠️  Banco não encontrado. Será criado: {db_path}")
        return db_path

def is_port_open(port=8501):
    """Verifica se a porta está em uso"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("localhost", port)) == 0
    except:
        return False

def main():
    print("=" * 50)
    print("🚀 HORUS FINANCEIRO - Pasta dist/")
    print("=" * 50)
    
    # Verificar dependências
    if not check_dependencies():
        print("\n💡 Instale as dependências primeiro.")
        if sys.platform == "win32":
            input("Pressione Enter para sair...")
        return
    
    # Encontrar main.py
    main_path = find_main_path()
    if not main_path:
        print("❌ Não foi possível encontrar o arquivo principal.")
        if sys.platform == "win32":
            input("Pressione Enter para sair...")
        return
    
    # Configurar banco na pasta dist
    db_path = find_or_create_db()
    
    print(f"📁 Main: {main_path}")
    print(f"💾 Banco: {db_path}")
    print("=" * 50)
    
    # Verificar se já está rodando
    if is_port_open(8501):
        print("⚠️  Já está rodando em http://localhost:8501")
        webbrowser.open("http://localhost:8501")
        if sys.platform == "win32":
            input("Pressione Enter para sair...")
        return
    
    print("🎯 Iniciando servidor...")
    print("🔗 Acesse: http://localhost:8501")
    print("⏹️  Para parar: Ctrl+C")
    print("=" * 50)
    
    # Configurar variáveis de ambiente
    env = os.environ.copy()
    env["HORUS_DB_PATH"] = db_path
    
    try:
        # Comando Streamlit
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", main_path,
            "--server.port=8501",
            "--server.headless=false"
        ], env=env)
        
        # Aguardar e abrir navegador
        time.sleep(5)
        if not is_port_open(8501):
            print("⏳ Aguardando servidor...")
            time.sleep(5)
        
        webbrowser.open("http://localhost:8501")
        
        # Manter rodando
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Parando servidor...")
        if process:
            process.terminate()
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        print("👋 Encerrado.")

if __name__ == "__main__":
    main()