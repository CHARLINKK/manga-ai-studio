"""Script de diagnóstico para rodar DENTRO do exe compilado."""
import sys
import os
import shutil
import winreg
from pathlib import Path

lines = []
lines.append(f"sys.executable    = {sys.executable}")
lines.append(f"sys.frozen        = {getattr(sys, 'frozen', False)}")
lines.append(f"__file__          = {__file__}")
lines.append(f"Path(__file__).parent = {Path(__file__).parent}")
lines.append(f"sys.argv[0]       = {sys.argv[0]}")
lines.append(f"Path(sys.argv[0]).parent = {Path(sys.argv[0]).parent}")

# simula get_python_exe
python_found = None
for candidate in ("python", "python3", "py"):
    found = shutil.which(candidate)
    if found:
        python_found = found
        break

if not python_found:
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for arch in (winreg.KEY_READ, winreg.KEY_READ | winreg.KEY_WOW64_32KEY):
            try:
                base = winreg.OpenKey(hive, r"SOFTWARE\Python\PythonCore", 0, arch)
                count = winreg.QueryInfoKey(base)[0]
                versions = [winreg.EnumKey(base, i) for i in range(count)]
                versions.sort(reverse=True)
                for ver in versions:
                    try:
                        key = winreg.OpenKey(base, rf"{ver}\InstallPath")
                        install_path, _ = winreg.QueryValueEx(key, "ExecutablePath")
                        if Path(install_path).exists():
                            python_found = install_path
                            break
                    except Exception:
                        continue
                if python_found:
                    break
            except Exception:
                continue
        if python_found:
            break

lines.append(f"python_found      = {python_found}")

# Testa caminhos de APP_SCRIPT
lines.append(f"app.py via __file__   = {Path(__file__).parent / 'app.py'} exists={( Path(__file__).parent / 'app.py').exists()}")
lines.append(f"app.py via argv[0]    = {Path(sys.argv[0]).parent / 'app.py'} exists={(Path(sys.argv[0]).parent / 'app.py').exists()}")
lines.append(f"app.py via exe path   = {Path(sys.executable).parent / 'app.py'} exists={(Path(sys.executable).parent / 'app.py').exists()}")

output = "\n".join(lines)
# Salva num arquivo txt ao lado do exe para visualizar
out_path = Path(sys.argv[0]).parent / "wizard_debug.txt"
out_path.write_text(output, encoding="utf-8")

import tkinter as tk
import tkinter.messagebox as mb
root = tk.Tk()
root.withdraw()
mb.showinfo("Debug Info", output)
root.destroy()
