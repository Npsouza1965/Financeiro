# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import webbrowser
import socket
import time
import signal
import shutil

# ============================================
# Sistema Financeiro Hórus - Launcher GitHub
# ============================================

def setup_environment():
    """Configura o ambiente e instala dependências se necessário"""
    print("🔧 Configurando ambiente...")
    
    # Lista de dependências necessárias
    dependencies = [
        'streamlit',
        'pandas', 
        'numpy',
        'matplotlib',
        'plotly',
        'reportlab',
        'fpdf',
        'sqlite3'
    ]
    
    # Tentar importar para verificar se estão instaladas
    missing_deps = []
    for dep in dependencies:
        try:
            if dep == 'sqlite3':
                import sqlite3
            else:
                __import__(dep)
        except ImportError:
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"📦 Instalando dependências faltantes: {', '.join(missing_deps)}")
        try:
            python_exec = get_real_python()
            if python_exec:
                subprocess.check_call([python_exec, "-m", "pip", "install"] + missing_deps)
                print("✅ Dependências instaladas com sucesso!")
            else:
                print("❌ Não foi possível instalar dependências automaticamente")
                print("💡 Execute: pip install " + " ".join(missing_deps))
        except Exception as e:
            print(f"❌ Erro na instalação: {e}")

def find_main_path():
    """Localiza o main.py - Versão GitHub"""
    # Primeiro tenta na estrutura local do projeto
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'modulos', 'main.py'),
        os.path.join(os.path.dirname(__file__), 'main.py'),
        'modulos/main.py',
        'main.py'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Main encontrado: {path}")
            return path
    
    # Se não encontrou, procura recursivamente
    for root, dirs, files in os.walk('.'):
        if 'main.py' in files:
            found_path = os.path.join(root, 'main.py')
            print(f"✅ Main encontrado (busca recursiva): {found_path}")
            return found_path
    
    print("❌ Arquivo main.py não encontrado")
    return None

def find_or_create_db():
    """Localiza ou cria banco de dados"""
    db_path = os.path.join(os.path.dirname(__file__), 'nps_financeiro.db')
    
    if os.path.exists(db_path):
        print(f"✅ Banco de dados encontrado: {db_path}")
        return db_path
    else:
        print(f"⚠️ Banco de dados não encontrado em: {db_path}")
        print("💡 Será criado um banco vazio na primeira execução")
        return db_path

def is_port_open(port=8501):
    """Verifica se a porta do Streamlit está em uso"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("localhost", port)) == 0
    except:
        return False

def wait_for_streamlit(port=8501, timeout=25):
    """Aguarda o servidor iniciar"""
    print("⏳ Aguardando servidor Streamlit...")
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port):
            return True
        time.sleep(0.5)
    return False

def get_real_python():
    """Localiza o interpretador Python do sistema"""
    candidates = [
        sys.executable,  # Python atual
        shutil.which("python"),
        shutil.which("python3"),
        shutil.which("py"),
    ]
    
    for path in candidates:
        if path and os.path.exists(path):
            return path
    
    print("⚠️ Python de sistema não encontrado, usando sys.executable")
    return sys.executable

def main():
    print("=" * 50)
    print("🚀 INICIANDO HORUS FINANCEIRO - GitHub Version")
    print("=" * 50)
    
    # Configurar ambiente
    setup_environment()
    
    # Localizar arquivos
    main_path = find_main_path()
    if not main_path:
        print("❌ Não foi possível encontrar o arquivo principal.")
        input("Pressione Enter para sair...")
        return
    
    db_path = find_or_create_db()
    
    print(f"📁 Main: {main_path}")
    print(f"💾 Banco: {db_path}")
    print("=" * 50)
    
    # Verificar se já está rodando
    if is_port_open(8501):
        print("⚠️  Já existe uma instância do Hórus em execução.")
        print("💡 Abrindo navegador...")
        webbrowser.open("http://localhost:8501")
        input("\nPressione Enter para sair...")
        return
    
    # Configurar ambiente
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["HORUS_DB_PATH"] = db_path  # Variável de ambiente para o banco
    
    # Obter Python
    python_exec = get_real_python()
    print(f"🐍 Usando Python: {python_exec}")
    
    # Comando Streamlit
    cmd = [
        python_exec, "-m", "streamlit", "run", main_path,
        "--server.port=8501",
        "--server.headless=false",
        "--server.runOnSave=true",
        "--browser.gatherUsageStats=false",
        "--theme.base=light"
    ]
    
    print("🎯 Iniciando servidor Streamlit...")
    print(f"🔗 URL: http://localhost:8501")
    print("⏹️  Para parar: Ctrl+C no terminal")
    print("=" * 50)
    
    try:
        # Iniciar processo
        process = subprocess.Popen(cmd, env=env)
        
        # Aguardar e abrir navegador
        if wait_for_streamlit():
            print("✅ Streamlit iniciado com sucesso!")
            print("🌐 Abrindo navegador...")
            webbrowser.open("http://localhost:8501")
        else:
            print("⚠️  Streamlit demorou para iniciar, verifique manualmente.")
            webbrowser.open("http://localhost:8501")
        
        # Aguardar processo
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Parando servidor...")
        if process:
            process.terminate()
    except Exception as e:
        print(f"❌ Erro ao iniciar: {e}")
    finally:
        print("👋 Hórus encerrado.")

if __name__ == "__main__":
    main()