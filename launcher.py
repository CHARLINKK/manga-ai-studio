#!/usr/bin/env python3
"""
Manga AI Studio - Launcher
Localiza o Python instalado e abre o app.py sem exibir terminal.
"""
import sys
import os
import shutil
import winreg
import subprocess
from pathlib import Path


def find_python(install_dir: Path) -> str:
    """
    Procura o python do venv_ui primeiro.
    """
    # 1. Prioridade máxima: venv_ui local (criado pelo instalador com todas as dependências da interface)
    local_venv = install_dir / "venv_ui" / "Scripts" / "python.exe"
    if local_venv.exists():
        return str(local_venv)

    # 2. Tenta o Python do sistema via PATH como fallback
    for candidate in ("python", "python3", "py"):
        found = shutil.which(candidate)
        if found:
            try:
                r = subprocess.run([found, "--version"], capture_output=True, text=True, timeout=5)
                if "Python 3" in (r.stdout + r.stderr):
                    return found
            except Exception:
                continue

    return None


def show_error(title: str, message: str):
    """Mostra uma caixa de erro sem depender do CTk."""
    try:
        import tkinter as tk
        import tkinter.messagebox as mb
        root = tk.Tk()
        root.withdraw()
        mb.showerror(title, message)
        root.destroy()
    except Exception:
        pass


def main():
    if getattr(sys, 'frozen', False):
        install_dir = Path(sys.executable).parent
    else:
        install_dir = Path(__file__).parent

    app_script = install_dir / "app.py"

    if not app_script.exists():
        show_error(
            "Manga AI Studio – Erro",
            f"O arquivo app.py não foi encontrado em:\n{install_dir}\n\n"
            "Execute o instalador (Manga_AI_Studio_Setup.exe) novamente."
        )
        return

    python_exe = find_python(install_dir)
    if not python_exe:
        show_error(
            "Manga AI Studio – Erro",
            "O ambiente venv_ui não foi encontrado e o Python 3 não está no sistema.\n\n"
            "Reinstale o aplicativo."
        )
        return

    # O launcher abre o app.py, que cuidará de inicializar a interface
    # Na primeira vez que o app é aberto numa máquina, bibliotecas de UI podem compilar caches de fontes.
    try:
        subprocess.Popen(
            [python_exe, str(app_script)],
            cwd=str(install_dir),
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
    except Exception as e:
        show_error(
            "Manga AI Studio – Erro ao Iniciar",
            f"Não foi possível abrir o programa.\n\n"
            f"Erro: {e}"
        )


if __name__ == "__main__":
    main()
