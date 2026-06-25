import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# We will append the methods to the end of the file, just before the `if __name__ == "__main__":` block.
methods = """
    def check_module_ocr(self):
        try:
            import easyocr
            import paddleocr
            import cv2
            return True
        except ImportError:
            return False

    def check_module_translation(self):
        import shutil
        import subprocess
        if not shutil.which("ollama"):
            return False
        try:
            r = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            return "gemma3:4b" in r.stdout
        except:
            return False

    def setup_modules_tab(self):
        self.frame_modules = ctk.CTkFrame(self.tab_modules, fg_color="transparent")
        self.frame_modules.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.frame_modules, text="Gerenciador de Módulos (IA)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 20))
        ctk.CTkLabel(self.frame_modules, text="Instale apenas o que você precisa. Módulos pesados são opcionais.", font=ctk.CTkFont(size=14), text_color="#ccc").pack(anchor="w", pady=(0, 20))

        # Card OCR
        self.card_ocr = ctk.CTkFrame(self.frame_modules, fg_color="#1a1a2e", corner_radius=10)
        self.card_ocr.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(self.card_ocr, text="📚 Motor de Extração de Texto (OCR)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.card_ocr, text="Necessário para a Etapa 1 (Extrair texto das imagens). Tamanho: ~3 GB", font=ctk.CTkFont(size=12), text_color="#aaa").pack(anchor="w", padx=15, pady=(0, 10))
        
        self.lbl_status_ocr = ctk.CTkLabel(self.card_ocr, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_ocr.pack(side="left", padx=15, pady=15)
        
        self.btn_install_ocr = ctk.CTkButton(self.card_ocr, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_ocr)
        self.btn_install_ocr.pack(side="right", padx=15, pady=15)
        
        self.log_ocr = ctk.CTkTextbox(self.card_ocr, height=100, state="disabled", fg_color="#000")

        # Card Translate
        self.card_trans = ctk.CTkFrame(self.frame_modules, fg_color="#16213e", corner_radius=10)
        self.card_trans.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(self.card_trans, text="🌍 Motor de Tradução e Polimento (IA)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.card_trans, text="Necessário para Etapas 2 e 3 (Gemma + Ollama). Tamanho: ~4 GB", font=ctk.CTkFont(size=12), text_color="#aaa").pack(anchor="w", padx=15, pady=(0, 10))
        
        self.lbl_status_trans = ctk.CTkLabel(self.card_trans, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_trans.pack(side="left", padx=15, pady=15)
        
        self.btn_install_trans = ctk.CTkButton(self.card_trans, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_translation)
        self.btn_install_trans.pack(side="right", padx=15, pady=15)
        
        self.log_trans = ctk.CTkTextbox(self.card_trans, height=100, state="disabled", fg_color="#000")

        self.refresh_module_status()

    def refresh_module_status(self):
        has_ocr = self.check_module_ocr()
        if has_ocr:
            self.lbl_status_ocr.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
            self.btn_install_ocr.configure(state="disabled", fg_color="#444", text="Já Instalado")
        else:
            self.lbl_status_ocr.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
            self.btn_install_ocr.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar (Lento)")

        has_trans = self.check_module_translation()
        if has_trans:
            self.lbl_status_trans.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
            self.btn_install_trans.configure(state="disabled", fg_color="#444", text="Já Instalado")
        else:
            self.lbl_status_trans.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
            self.btn_install_trans.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar (Lento)")

    def _ui_log(self, box, text):
        def _append():
            box.configure(state="normal")
            box.insert("end", text + "\\n")
            box.see("end")
            box.configure(state="disabled")
        self.after(0, _append)

    def install_ocr(self):
        self.btn_install_ocr.configure(state="disabled", text="Instalando...")
        self.log_ocr.pack(fill="x", padx=15, pady=(0, 15))
        self.log_ocr.configure(state="normal")
        self.log_ocr.delete("0.0", "end")
        self.log_ocr.configure(state="disabled")
        
        def worker():
            try:
                import sys
                import subprocess
                self._ui_log(self.log_ocr, "Iniciando instalação das bibliotecas de Visão Computacional e PyTorch...")
                req = Path(__file__).parent / "requirements-ocr.txt"
                if not req.exists():
                    self._ui_log(self.log_ocr, "❌ Arquivo requirements-ocr.txt não encontrado!")
                    return

                cmd = [sys.executable, "-m", "pip", "install", "-r", str(req)]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                for line in proc.stdout:
                    self._ui_log(self.log_ocr, line.strip()[:100])
                proc.wait()
                
                if proc.returncode == 0:
                    self._ui_log(self.log_ocr, "✅ Instalação concluída com sucesso!")
                else:
                    self._ui_log(self.log_ocr, f"❌ Erro na instalação. Código: {proc.returncode}")
            except Exception as e:
                self._ui_log(self.log_ocr, f"❌ Exceção: {e}")
            finally:
                self.after(0, self.refresh_module_status)
        
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def install_translation(self):
        self.btn_install_trans.configure(state="disabled", text="Instalando...")
        self.log_trans.pack(fill="x", padx=15, pady=(0, 15))
        self.log_trans.configure(state="normal")
        self.log_trans.delete("0.0", "end")
        self.log_trans.configure(state="disabled")

        def worker():
            import shutil
            import urllib.request
            import tempfile
            import subprocess
            try:
                if not shutil.which("ollama"):
                    self._ui_log(self.log_trans, "▶ Ollama não detectado. Baixando instalador (~60 MB)...")
                    url = "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
                    dest = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
                    urllib.request.urlretrieve(url, dest)
                    self._ui_log(self.log_trans, "▶ Instalando Ollama (pode pedir permissão de Admin)...")
                    subprocess.run([str(dest), "/SILENT"], capture_output=True)
                    if not shutil.which("ollama"):
                        self._ui_log(self.log_trans, "❌ Falha ao instalar Ollama. Tente instalar manualmente.")
                        return
                    self._ui_log(self.log_trans, "✅ Ollama instalado com sucesso.")

                self._ui_log(self.log_trans, "▶ Baixando modelo gemma3:4b (isso demorará dependendo da internet)...")
                proc = subprocess.Popen(["ollama", "pull", "gemma3:4b"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                for line in proc.stdout:
                    if line.strip():
                        self._ui_log(self.log_trans, line.strip())
                proc.wait()
                
                if proc.returncode == 0:
                    self._ui_log(self.log_trans, "✅ IA de Tradução instalada e pronta para uso!")
                else:
                    self._ui_log(self.log_trans, "❌ Erro ao baixar o modelo.")
            except Exception as e:
                self._ui_log(self.log_trans, f"❌ Exceção: {e}")
            finally:
                self.after(0, self.refresh_module_status)
                
        import threading
        threading.Thread(target=worker, daemon=True).start()

"""

# Inject before if __name__ == "__main__":
if 'if __name__ == "__main__":' in code:
    code = code.replace('if __name__ == "__main__":', methods + '\n\nif __name__ == "__main__":')
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Methods injected.")
else:
    print("Could not find __main__ block.")
