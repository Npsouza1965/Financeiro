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
# Sistema Financeiro Hórus - Launcher PyInstaller
# ============================================

def find_main_path():
    """Localiza o main.py"""
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, 'modulos', 'main.py')


def find_db_path():
    """Banco de dados junto ao executável"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.join(os.getcwd(), 'dist')
    return os.path.join(base_dir, 'nps_financeiro.db')


def is_port_open(port=8501):
    """Verifica se a porta do Streamlit está em uso"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", port)) == 0


def wait_for_streamlit(port=8501, timeout=25):
    """Aguarda o servidor iniciar"""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port):
            return True
        time.sleep(0.5)
    return False


def get_real_python():
    """
    Tenta localizar o interpretador Python do sistema.
    Evita usar o exe congelado (que causa loop).
    """
    candidates = [
        shutil.which("python"),
        shutil.which("python3"),
        os.path.join(sys.exec_prefix, "python.exe")
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    print("⚠️  Python de sistema não encontrado.")
    return None


def main():
    print("INICIANDO HORUS FINANCEIRO...")

    main_path = find_main_path()
    db_path = find_db_path()

    print(f"Arquivo principal: {main_path}")
    print(f"Banco de dados: {db_path}")
    print("=" * 50)

    if is_port_open(8501):
        print("⚠️  Já existe uma instância do Hórus em execução.")
        input("\nPressione Enter para sair...")
        return

    python_exec = get_real_python()
    if not python_exec:
        print("❌ Não foi possível localizar o interpretador Python do sistema.")
        input("Pressione Enter para sair...")
        return

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Comando de execução (streamlit via python real)
    cmd = [
        python_exec, "-m", "streamlit", "run", main_path,
        "--server.port=8501",
        "--server.headless=true",
        "--server.runOnSave=false",
        "--browser.gatherUsageStats=false"
    ]

    print(f"Executando com: {python_exec}")
    print("Iniciando servidor Streamlit...")

    try:
        process = subprocess.Popen(cmd, env=env)

        if wait_for_streamlit():
            print("✅ Streamlit iniciado com sucesso!")
            webbrowser.open("http://localhost:8501")
        else:
            print("⚠️  Streamlit não iniciou no tempo esperado.")

        process.wait()
    except Exception as e:
        print(f"❌ Erro ao iniciar: {e}")
    finally:
        input("\nAplicativo encerrado. Pressione Enter para sair...")


if __name__ == "__main__":
    main()
