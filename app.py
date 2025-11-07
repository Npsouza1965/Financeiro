# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import webbrowser
import socket
import time
import shutil

# ============================================
# Sistema Financeiro Hórus - Launcher GitHub
# ============================================

def setup_environment():
    """Configura o ambiente de forma mais robusta"""
    print("🔧 Configurando ambiente...")
    
    # Lista de dependências essenciais (em ordem de importância)
    dependencies = [
        'streamlit',
        'pandas', 
        'numpy',
        'matplotlib',
        'plotly',
        'reportlab',
        'fpdf2'  # Note: fpdf foi renomeado para fpdf2
    ]
    
    print("📦 Verificando dependências...")
    
    # Verificar quais dependências estão faltando
    missing_deps = []
    for dep in dependencies:
        try:
            if dep == 'fpdf2':
                __import__('fpdf')
            else:
                __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            missing_deps.append(dep)
            print(f"   ❌ {dep}")
    
    if not missing_deps:
        print("✅ Todas as dependências estão instaladas!")
        return True
    
    print(f"⚠️  Dependências faltantes: {', '.join(missing_deps)}")
    
    # Tentar instalar as dependências faltantes
    python_exec = get_real_python()
    if not python_exec:
        print("❌ Não foi possível encontrar o Python para instalação")
        return False
    
    try:
        print("📥 Instalando dependências...")
        
        # Instalar uma por uma para melhor debug
        for dep in missing_deps:
            print(f"   📥 Instalando {dep}...")
            if dep == 'fpdf2':
                # fpdf foi renomeado para fpdf2
                result = subprocess.run(
                    [python_exec, "-m", "pip", "install", "fpdf2"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            else:
                result = subprocess.run(
                    [python_exec, "-m", "pip", "install", dep],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            
            if result.returncode == 0:
                print(f"   ✅ {dep} instalado com sucesso!")
            else:
                print(f"   ❌ Falha ao instalar {dep}: {result.stderr}")
                return False
                
        print("✅ Todas as dependências instaladas com sucesso!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout na instalação das dependências")
        return False
    except Exception as e:
        print(f"❌ Erro na instalação: {e}")
        return False

def find_main_path():
    """Localiza o main.py de forma mais robusta"""
    print("🔍 Procurando arquivo principal...")
    
    # Possíveis locais do main.py
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'modulos', 'main.py'),
        os.path.join(os.path.dirname(__file__), 'main.py'),
        'modulos/main.py',
        'main.py',
        os.path.join('src', 'modulos', 'main.py'),
        os.path.join('src', 'main.py')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Main encontrado: {path}")
            return path
    
    # Busca recursiva como fallback
    print("🔍 Buscando recursivamente...")
    for root, dirs, files in os.walk('.'):
        if 'main.py' in files:
            found_path = os.path.join(root, 'main.py')
            print(f"✅ Main encontrado (busca recursiva): {found_path}")
            return found_path
    
    print("❌ Arquivo main.py não encontrado em nenhum local")
    return None

def find_or_create_db():
    """Localiza ou cria banco de dados"""
    possible_db_paths = [
        os.path.join(os.path.dirname(__file__), 'nps_financeiro.db'),
        os.path.join(os.path.dirname(__file__), 'database', 'nps_financeiro.db'),
        'nps_financeiro.db',
        os.path.join('data', 'nps_financeiro.db')
    ]
    
    for db_path in possible_db_paths:
        if os.path.exists(db_path):
            print(f"✅ Banco de dados encontrado: {db_path}")
            return db_path
    
    # Se não encontrou, usa o primeiro caminho
    db_path = possible_db_paths[0]
    print(f"⚠️  Banco não encontrado. Será criado em: {db_path}")
    
    # Criar diretório se necessário
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path

def is_port_open(port=8501):
    """Verifica se a porta está em uso"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("localhost", port)) == 0
    except:
        return False

def wait_for_streamlit(port=8501, timeout=30):
    """Aguarda o servidor iniciar"""
    print("⏳ Aguardando servidor Streamlit...")
    start = time.time()
    
    for i in range(timeout):
        if is_port_open(port):
            print("✅ Servidor Streamlit pronto!")
            return True
        if i % 5 == 0:  # Mostrar progresso a cada 5 segundos
            print(f"   ...{i}/{timeout} segundos")
        time.sleep(1)
    
    print("⚠️  Servidor demorou para iniciar")
    return False

def get_real_python():
    """Localiza o interpretador Python"""
    candidates = [
        sys.executable,
        shutil.which("python"),
        shutil.which("python3"),
        shutil.which("py"),
        os.path.join(sys.prefix, "python.exe"),
    ]
    
    for path in candidates:
        if path and os.path.exists(path):
            return path
    
    return sys.executable  # Fallback

def main():
    print("=" * 60)
    print("🚀 HORUS FINANCEIRO - Launcher")
    print("=" * 60)
    
    # Configurar ambiente
    if not setup_environment():
        print("\n❌ Erro na configuração do ambiente.")
        print("💡 Soluções possíveis:")
        print("   1. Execute manualmente: pip install -r requirements.txt")
        print("   2. Verifique sua conexão com internet")
        print("   3. Tente reiniciar o aplicativo")
        input("\nPressione Enter para sair...")
        return
    
    # Localizar arquivos
    main_path = find_main_path()
    if not main_path:
        print("❌ Não foi possível encontrar o arquivo principal.")
        input("Pressione Enter para sair...")
        return
    
    db_path = find_or_create_db()
    
    print(f"📁 Main: {main_path}")
    print(f"💾 Banco: {db_path}")
    print("=" * 60)
    
    # Verificar se já está rodando
    if is_port_open(8501):
        print("⚠️  Já existe uma instância em execução.")
        print("💡 Abrindo navegador...")
        webbrowser.open("http://localhost:8501")
        input("\nPressione Enter para sair...")
        return
    
    # Configurar ambiente
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["HORUS_DB_PATH"] = db_path
    
    # Obter Python
    python_exec = get_real_python()
    print(f"🐍 Python: {python_exec}")
    
    # Comando Streamlit
    cmd = [
        python_exec, "-m", "streamlit", "run", main_path,
        "--server.port=8501",
        "--server.headless=false",
        "--server.runOnSave=true",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false"
    ]
    
    print("🎯 Iniciando servidor...")
    print("🔗 Acesse: http://localhost:8501")
    print("⏹️  Para parar: Ctrl+C")
    print("=" * 60)
    
    try:
        process = subprocess.Popen(cmd, env=env)
        
        if wait_for_streamlit():
            print("🌐 Abrindo navegador...")
            webbrowser.open("http://localhost:8501")
        else:
            print("⚠️  Verifique manualmente: http://localhost:8501")
        
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