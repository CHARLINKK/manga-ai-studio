import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

update_code = """
    def check_for_updates(self):
        import urllib.request
        import json
        from tkinter import messagebox
        import sys
        import subprocess
        
        url_version = "https://raw.githubusercontent.com/SEU_USUARIO_AQUI/MangaAIStudio/main/version.json"
        url_zip = "https://github.com/SEU_USUARIO_AQUI/MangaAIStudio/archive/refs/heads/main.zip"
        
        self.log_ocr.configure(state="normal") # usando o log_ocr apenas para exibir mensagem temporaria ou a gente cria popup
        try:
            req = urllib.request.Request(url_version, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                remote_data = json.loads(response.read().decode())
                
            remote_version = remote_data.get("version", "1.0.0")
            
            # Lê versão local
            local_version = "1.0.0"
            version_file = Path("version.json")
            if version_file.exists():
                with open(version_file, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    local_version = local_data.get("version", "1.0.0")
                    
            if remote_version != local_version:
                msg = f"Nova versão encontrada: {remote_version}\\nNovidades: {remote_data.get('changelog', '')}\\n\\nDeseja atualizar agora?"
                if messagebox.askyesno("Atualização Disponível", msg):
                    updater_path = Path("updater.py")
                    if updater_path.exists():
                        # Lança o updater
                        sys_python = Path("venv/Scripts/python.exe") if Path("venv/Scripts/python.exe").exists() else Path(sys.executable)
                        subprocess.Popen(f'start cmd /c "{sys_python} updater.py --url {url_zip}"', shell=True)
                        self.destroy()
                    else:
                        messagebox.showerror("Erro", "Script updater.py não encontrado.")
            else:
                messagebox.showinfo("Atualizado", "Você já está usando a versão mais recente!")
                
        except Exception as e:
            messagebox.showerror("Erro de Atualização", f"Não foi possível checar por atualizações.\\nDetalhes: {e}")
            
    def setup_modules_tab(self):
"""

code = code.replace("    def setup_modules_tab(self):", update_code)

btn_code = """
        ctk.CTkLabel(self.frame_modules, text="Gerenciador de Módulos (IA)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 20))
        
        self.btn_update_app = ctk.CTkButton(self.frame_modules, text="🔄 Verificar Atualizações do App", fg_color="#3498db", hover_color="#2980b9", command=self.check_for_updates)
        self.btn_update_app.place(relx=0.98, rely=0.0, anchor="ne")

        ctk.CTkLabel(self.frame_modules, text="Instale apenas o que você precisa. Módulos pesados são opcionais.", font=ctk.CTkFont(size=14), text_color="#ccc").pack(anchor="w", pady=(0, 20))
"""

target = """        ctk.CTkLabel(self.frame_modules, text="Gerenciador de Módulos (IA)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 20))
        ctk.CTkLabel(self.frame_modules, text="Instale apenas o que você precisa. Módulos pesados são opcionais.", font=ctk.CTkFont(size=14), text_color="#ccc").pack(anchor="w", pady=(0, 20))"""

code = code.replace(target, btn_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Updater UI injected.")
