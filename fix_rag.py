import shutil

# shutil.copy('app.py.bak4', 'app.py') # No need to restore, just fix the current file

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

bad_code = """        def worker():
            import subprocess
            import sys
            import venv
            import os
            
            self._ui_log(self.log_rag, " Baixando e instalando ChromaDB e SentenceTransformers (pode demorar)...")
            
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
                
            if getattr(sys, 'frozen', False):
                python_exe = "python"
            else:
                python_exe = sys.executable
                
            venv_path = install_dir / "venv_ui"
            if not venv_path.exists():
                subprocess.run([python_exe, "-m", "venv", str(venv_path)], capture_output=True, creationflags=0x08000000, startupinfo=startupinfo)
                
            pip_exe = str(venv_path / "Scripts" / "pip.exe")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            import os
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            
            proc = subprocess.Popen([pip_exe, "install", "chromadb", "sentence-transformers", "rapidfuzz"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000, startupinfo=startupinfo, env=env)
            
            has_downloaded = False
            has_installed = False
            for line in proc.stdout:
                if not line.strip(): continue
                l = line.lower()
                if ("download" in l or "fetching" in l) and not has_downloaded:
                    self._ui_log(self.log_rag, " [Etapa 2/3]  Baixando pacotes (isso pode demorar)...")
                    has_downloaded = True
                elif ("installing collected" in l or "running setup" in l) and not has_installed:
                    self._ui_log(self.log_rag, " [Etapa 3/3]  Instalando e configurando arquivos no sistema...")
                    has_installed = True
                    
                self.after(0, lambda: self._bump_progress(self.pb_rag))
            proc.wait()
            
            if proc.returncode == 0:
                self._ui_log(self.log_rag, " Motor RAG instalado com sucesso!")
            else:
                self._ui_log(self.log_rag, " Falha ao instalar dependências.")
            
            self.after(0, self.refresh_module_status)"""

good_code = """        def worker():
            import subprocess
            import sys
            import venv
            import os
            from pathlib import Path
            
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
                
            if getattr(sys, 'frozen', False):
                python_exe = "python"
            else:
                python_exe = sys.executable
                
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            venv_path = install_dir / "venv_ui"
            if not venv_path.exists():
                self._ui_log(self.log_rag, " [Etapa 1/3]  Criando ambiente virtual isolado...")
                subprocess.run([python_exe, "-m", "venv", str(venv_path)], capture_output=True, creationflags=0x08000000, startupinfo=startupinfo)
                
            pip_exe = str(venv_path / "Scripts" / "pip.exe")
            
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            
            self._ui_log(self.log_rag, " [Etapa 2/3]  Iniciando download via PIP (ChromaDB + Pacotes)...")
            proc = subprocess.Popen([pip_exe, "install", "chromadb", "sentence-transformers", "rapidfuzz"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000, startupinfo=startupinfo, env=env)
            
            for line in proc.stdout:
                line = line.strip()
                if not line: continue
                # Stream actual output so the user sees progress
                self._ui_log(self.log_rag, f" > {line}")
                self.after(0, lambda: self._bump_progress(self.pb_rag))
            proc.wait()
            
            if proc.returncode == 0:
                self._ui_log(self.log_rag, " [Etapa 3/3]  Motor RAG instalado com sucesso!")
            else:
                self._ui_log(self.log_rag, " ❌ Falha crítica ao instalar dependências.")
            
            self.after(0, self.refresh_module_status)"""

if bad_code in code:
    code = code.replace(bad_code, good_code)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("RAG fix applied successfully!")
else:
    print("Target code not found! Trying fallback replace...")
