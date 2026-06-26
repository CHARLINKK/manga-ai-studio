import os
import sys
import subprocess
import threading
import shutil
import urllib.request
import winreg
from pathlib import Path

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

import traceback
import sys

def global_exception_handler(exctype, value, tb):
    with open("setup_crash.log", "a") as f:
        f.write("".join(traceback.format_exception(exctype, value, tb)))
sys.excepthook = global_exception_handler

# --- Constantes ---
VERSION = "1.3.3"
PYTHON_DOWNLOAD_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
TEMP_DIR = Path(os.environ.get("TEMP", "C:/Temp")) / "MangaAIStudioSetup"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

INSTALL_DIR_DEFAULT = Path("C:/MangaAIStudio")

PROGRAM_FILES = [
    "app.py",
    "manga_ocr.py",
    "manga_translator.py",
    "ocr_corrector.py",
    "requirements.txt",
    "requirements-ocr.txt",
    "icon.ico",
    "version.json"
]

STEPS = [
    "Boas Vindas",
    "Instalar Python",
    "Copiar Arquivos",
    "Dependências",
    "Concluir"
]

C_BG      = "#1a1a2e"
C_SURFACE = "#16213e"
C_ACCENT  = "#e74c3c"
C_GREEN   = "#2ecc71"
C_YELLOW  = "#f1c40f"
C_MUTED   = "#a0aabf"
C_RED     = "#e74c3c"

def get_bundled_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

def check_python() -> tuple[bool, bool, str]:
    try:
        r = subprocess.run(["py", "-3.12", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"], capture_output=True, text=True, timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode == 0:
            ver = r.stdout.strip()
            return (True, ver.startswith("3.12"), ver)
    except Exception:
        pass
    
    try:
        r = subprocess.run(["python", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"], capture_output=True, text=True, timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode == 0:
            ver = r.stdout.strip()
            return (True, ver.startswith("3.12"), ver)
    except Exception:
        pass
    
    return (False, False, "")

def download_file(url: str, dest: Path, progress_cb=None, log_cb=None):
    def reporthook(blocknum, blocksize, totalsize):
        if totalsize > 0 and progress_cb:
            read = blocknum * blocksize
            p = min(read / totalsize, 1.0)
            progress_cb(p)
    urllib.request.urlretrieve(url, str(dest), reporthook)

def create_shortcut(target: Path, name: str, icon: Path = None, dest_dir: Path = None, arguments: str = "", working_dir: Path = None):
    try:
        desktop = dest_dir if dest_dir else (Path(os.environ["USERPROFILE"]) / "Desktop")
        shortcut_path = desktop / f"{name}.lnk"
        wdir = working_dir if working_dir else target.parent
        
        script = f"""
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.Arguments = "{arguments}"
$Shortcut.WorkingDirectory = "{wdir}"
"""
        if icon and icon.exists():
            script += f'$Shortcut.IconLocation = "{icon}"\n'
        script += "$Shortcut.Save()\n"
        
        subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Erro ao criar atalho: {e}")


class SetupWizard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Manga AI Studio – Instalador")
        w, h = 860, 620
        self.geometry(f"{w}x{h}")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)

        self.install_dir = INSTALL_DIR_DEFAULT
        self.current_step = 0
        
        icon_path = get_bundled_dir() / "icon.ico"
        if icon_path.exists():
            try: self.iconbitmap(str(icon_path))
            except: pass

        self.is_silent = "--silent" in sys.argv
        if self.is_silent:
            self.withdraw()  # Torna a janela 100% invisível
            self.title("Manga AI Studio – Atualizando...")
            self.lbl_title = None

        self._build_shell()
        self.after(200, self._run_step_0)

    def _build_shell(self):
        root = ctk.CTkFrame(self, fg_color=C_BG)
        root.pack(fill="both", expand=True)
        
        self.sidebar = ctk.CTkFrame(root, width=280, fg_color="#12182b", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        lbl_logo = ctk.CTkLabel(self.sidebar, text="📖", font=ctk.CTkFont(size=50))
        lbl_logo.pack(pady=(40, 10))
        
        ctk.CTkLabel(self.sidebar, text="Manga AI Studio", font=ctk.CTkFont(size=20, weight="bold"), text_color="white").pack()
        ctk.CTkLabel(self.sidebar, text="Instalador Completo", font=ctk.CTkFont(size=13), text_color=C_MUTED).pack(pady=(0, 40))
        
        self.step_labels = []
        for i, text in enumerate(STEPS):
            frm = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            frm.pack(fill="x", padx=30, pady=8)
            dot = ctk.CTkLabel(frm, text="●", font=ctk.CTkFont(size=16), text_color=C_MUTED, width=20)
            dot.pack(side="left")
            lbl = ctk.CTkLabel(frm, text=f"{i+1}. {text}", font=ctk.CTkFont(size=13), text_color=C_MUTED)
            lbl.pack(side="left", padx=(10, 0))
            self.step_labels.append((dot, lbl))
            
        self.content_area = ctk.CTkFrame(root, fg_color=C_BG, corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True)
        
        self.header_frame = ctk.CTkFrame(self.content_area, fg_color="transparent", height=100)
        self.header_frame.pack(fill="x", padx=36, pady=(36, 10))
        self.header_frame.pack_propagate(False)
        
        self.lbl_title = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=26, weight="bold"), text_color="white", anchor="w")
        self.lbl_title.pack(fill="x")
        self.lbl_subtitle = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=14), text_color=C_MUTED, anchor="w")
        self.lbl_subtitle.pack(fill="x", pady=(4, 0))
        
        self.content = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.content.pack(fill="both", expand=True)

    def _update_sidebar(self):
        for i, (dot, lbl) in enumerate(self.step_labels):
            if i < self.current_step:
                dot.configure(text_color=C_GREEN)
                lbl.configure(text_color="white", font=ctk.CTkFont(size=13))
            elif i == self.current_step:
                dot.configure(text_color=C_ACCENT)
                lbl.configure(text_color="white", font=ctk.CTkFont(size=13, weight="bold"))
            else:
                dot.configure(text_color=C_MUTED)
                lbl.configure(text_color=C_MUTED, font=ctk.CTkFont(size=13))

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _header(self, title, subtitle):
        self.lbl_title.configure(text=title)
        self.lbl_subtitle.configure(text=subtitle)

    def _footer_buttons(self, back_cmd=None, buttons_right=None):
        frm = ctk.CTkFrame(self.content, fg_color="transparent", height=60)
        frm.pack(side="bottom", fill="x", pady=20)
        
        if back_cmd:
            ctk.CTkButton(frm, text="← Voltar", width=100, fg_color="transparent", border_width=1,
                          border_color=C_MUTED, hover_color=C_SURFACE, text_color="white",
                          command=back_cmd).pack(side="left", padx=36)
            
        if buttons_right:
            for btn_text, color, hover, cmd, attr_name in reversed(buttons_right):
                b = ctk.CTkButton(frm, text=btn_text, width=140, fg_color=color, hover_color=hover, command=cmd)
                b.pack(side="right", padx=(0, 36 if attr_name == buttons_right[0][4] else 10))
                if attr_name:
                    setattr(self, attr_name, b)

    def _status_row(self, parent, label, value, color):
        frm = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=6, height=44)
        frm.pack(fill="x", pady=4)
        frm.pack_propagate(False)
        ctk.CTkLabel(frm, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(side="left", padx=14)
        ctk.CTkLabel(frm, text=value, font=ctk.CTkFont(size=13, weight="bold"), text_color=color).pack(side="right", padx=14)

    def _log_box(self, parent):
        box = ctk.CTkTextbox(parent, height=130, fg_color="#0f1423", text_color="#d1d8e0", font=ctk.CTkFont(family="Consolas", size=11))
        box.pack(fill="x", pady=(14, 4))
        box.configure(state="disabled")
        return box

    def _log(self, box, text):
        box.configure(state="normal")
        box.insert("end", text + "\n")
        box.see("end")
        box.configure(state="disabled")

    # =========================================================
    # PASSO 0 - Boas Vindas & Destino
    # =========================================================
    def _run_step_0(self):
        self.current_step = 0
        self._update_sidebar()
        self._clear_content()
        self._header("Boas-vindas", "Configuração inicial e destino da instalação.")

        ctk.CTkLabel(self.content, text="O Instalador configurará o Manga AI Studio, criando um ambiente isolado\n"
                                        "para não interferir com outros projetos do seu computador.",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED, justify="left"
                     ).pack(anchor="w", padx=36, pady=(10, 20))

        ctk.CTkLabel(self.content, text="📁 Pasta de Instalação", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(anchor="w", padx=36, pady=(10, 4))
        
        dir_frm = ctk.CTkFrame(self.content, fg_color=C_SURFACE, corner_radius=8)
        dir_frm.pack(fill="x", padx=36)
        
        self.entry_dir = ctk.CTkEntry(dir_frm, font=ctk.CTkFont(size=12), width=340)
        self.entry_dir.insert(0, str(self.install_dir))
        self.entry_dir.pack(side="left", padx=14, pady=10, fill="x", expand=True)
        
        ctk.CTkButton(dir_frm, text="Alterar", width=90, fg_color="#2c3e7a", hover_color="#3d52a0", command=self._pick_dir).pack(side="right", padx=10, pady=10)

        self._footer_buttons(buttons_right=[("Próximo →", C_ACCENT, "#c0392b", self._confirm_dir, "btn0")])
        if self.is_silent:
            self.after(500, self._confirm_dir)

    def _pick_dir(self):
        import tkinter.filedialog as fd
        chosen = fd.askdirectory(title="Escolha a pasta", initialdir=str(self.install_dir.parent))
        if chosen:
            self.install_dir = Path(chosen) / "MangaAIStudio"
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, str(self.install_dir))

    def _confirm_dir(self):
        val = self.entry_dir.get().strip()
        if val:
            self.install_dir = Path(val)
        self._run_step_1()

    # =========================================================
    # PASSO 1 - Python
    # =========================================================
    def _run_step_1(self):
        self.current_step = 1
        self._update_sidebar()
        self._clear_content()

        py_found, py_ok, py_ver = check_python()
        
        if py_found and py_ok:
            self._header("Python ✅ Já Instalado", f"Python 3.12 detectado: {py_ver}. Nada a fazer.")
            area = ctk.CTkFrame(self.content, fg_color="transparent")
            area.pack(fill="x", padx=36)
            self._status_row(area, "Python 3.12", f"✅  {py_ver}", C_GREEN)
            self._footer_buttons(back_cmd=self._run_step_0, buttons_right=[("Próximo →", C_GREEN, "#27ae60", self._run_step_2, None)])
            if self.is_silent:
                self.after(500, self._run_step_2)
            return

        self._header("Instalação do Python", "Python 3.12 será baixado e instalado automaticamente.")
        area = ctk.CTkFrame(self.content, fg_color="transparent")
        area.pack(fill="x", padx=36)
        
        if py_found and not py_ok:
            self._status_row(area, "Python Incompatível", f"❌ Encontrado: {py_ver} (Requer 3.12)", C_RED)
        else:
            self._status_row(area, "Python", "❌  Não encontrado", C_RED)

        ctk.CTkLabel(area, text="Será baixado Python 3.12 (~25 MB) e instalado para todos os usuários.\nPermissão de administrador necessária.",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED, justify="left").pack(anchor="w", pady=(10, 4))

        self.log1 = self._log_box(area)
        self.bar1 = ctk.CTkProgressBar(area)
        self.bar1.pack(fill="x", pady=(6, 0))
        self.bar1.set(0)

        self._footer_buttons(back_cmd=self._run_step_0, buttons_right=[("⬇ Instalar Python", C_ACCENT, "#c0392b", self._do_install_python, "btn1_install")])
        if self.is_silent:
            self.after(500, self._do_install_python)

    def _do_install_python(self):
        self.btn1_install.configure(state="disabled", text="⏳ Baixando Python...")
        self.bar1.set(0)
        
        def worker():
            try:
                dest = TEMP_DIR / "python_installer.exe"
                self._log(self.log1, f"▶ Baixando Python...")
                download_file(PYTHON_DOWNLOAD_URL, dest, progress_cb=lambda p: self.bar1.set(p * 0.85), log_cb=lambda t: self._log(self.log1, t))
                self._log(self.log1, "\n✅ Download concluído. Solicitando instalação...")
                self.bar1.set(0.9)
                subprocess.run([str(dest), "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_pip=1"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.bar1.set(1.0)
                self.bar1.configure(progress_color=C_GREEN)
                py_f, py_o, py_v = check_python()
                if py_f and py_o:
                    self._log(self.log1, f"✅ Python instalado: {py_v}")
                    self.after(0, lambda: self.btn1_install.configure(text="✅ Próximo →", fg_color=C_GREEN, state="normal", command=self._run_step_2))
                    if self.is_silent:
                        self.after(500, self._run_step_2)
                else:
                    self._log(self.log1, "❌ Instalação concluída mas versão 3.12 não detectada. Reinicie o PC e tente novamente.")
                    self.after(0, lambda: self.btn1_install.configure(text="⬇ Tentar Novamente", state="normal"))
            except Exception as e:
                self._log(self.log1, f"❌ Erro: {e}")
                self.after(0, lambda: self.btn1_install.configure(text="⬇ Tentar Novamente", state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================
    # PASSO 2 - Copiar Arquivos
    # =========================================================
    def _run_step_2(self):
        self.current_step = 2
        self._update_sidebar()
        self._clear_content()
        self._header("Copiar Arquivos", "Transferindo os arquivos do Manga AI Studio para o destino.")

        area = ctk.CTkFrame(self.content, fg_color="transparent")
        area.pack(fill="x", padx=36)

        ctk.CTkLabel(area, text=f"Destino: {self.install_dir}", font=ctk.CTkFont(size=12, weight="bold"), text_color="white").pack(anchor="w")

        self.log2 = self._log_box(area)
        self.bar2 = ctk.CTkProgressBar(area)
        self.bar2.pack(fill="x", pady=(6, 0))
        self.bar2.set(0)

        self._footer_buttons(back_cmd=self._run_step_1, buttons_right=[("Iniciar Cópia", C_ACCENT, "#c0392b", self._do_copy_files, "btn2_copy")])
        if self.is_silent:
            self.after(500, self._do_copy_files)

    def _do_copy_files(self):
        self.btn2_copy.configure(state="disabled", text="⏳ Copiando...")
        self.bar2.set(0)

        def worker():
            try:
                self.install_dir.mkdir(parents=True, exist_ok=True)
                src_dir = get_bundled_dir()
                
                total = len(PROGRAM_FILES) + 1 # +1 for modules
                for i, fname in enumerate(PROGRAM_FILES):
                    src_file = src_dir / fname
                    dst_file = self.install_dir / fname
                    if src_file.exists():
                        self._log(self.log2, f"Copiando: {fname}")
                        shutil.copy2(src_file, dst_file)
                    else:
                        self._log(self.log2, f"Aviso: {fname} não encontrado no instalador.")
                    self.bar2.set((i+1) / total)
                
                # Copy modules folder if it exists
                src_modules = src_dir / "modules"
                dst_modules = self.install_dir / "modules"
                if src_modules.exists():
                    self._log(self.log2, f"Copiando: modules/")
                    if dst_modules.exists():
                        shutil.rmtree(dst_modules)
                    shutil.copytree(src_modules, dst_modules)
                self.bar2.set(1.0)
                self.bar2.configure(progress_color=C_GREEN)
                self._log(self.log2, "✅ Todos os arquivos foram copiados com sucesso!")
                
                self.after(0, lambda: self.btn2_copy.configure(text="✅ Próximo →", fg_color=C_GREEN, state="normal", command=self._run_step_3))
                if self.is_silent:
                    self.after(500, self._run_step_3)
            except Exception as e:
                self._log(self.log2, f"❌ Erro ao copiar arquivos: {e}")
                self.after(0, lambda: self.btn2_copy.configure(text="Tentar Novamente", state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================
    # PASSO 3 - Dependências (venv_ui)
    # =========================================================
    def _run_step_3(self):
        self.current_step = 3
        self._update_sidebar()
        self._clear_content()
        self._header("Dependências Python", "Criando ambiente virtual (venv_ui) e instalando dependências base.")

        area = ctk.CTkFrame(self.content, fg_color="transparent")
        area.pack(fill="x", padx=36)

        self.log3 = self._log_box(area)
        self.bar3 = ctk.CTkProgressBar(area)
        self.bar3.pack(fill="x", pady=(6, 0))
        self.bar3.set(0)

        site_packages = self.install_dir / "venv_ui" / "Lib" / "site-packages"
        if (site_packages / "customtkinter").exists():
            self.bar3.set(1.0)
            self.bar3.configure(progress_color=C_GREEN)
            self._log(self.log3, "✅ Dependências já estão instaladas no ambiente virtual!")
            self._footer_buttons(back_cmd=self._run_step_2, buttons_right=[("Próximo →", C_GREEN, "#27ae60", self._run_step_4, "btn3")])
            if self.is_silent:
                self.after(500, self._run_step_4)
        else:
            self._footer_buttons(back_cmd=self._run_step_2, buttons_right=[("⬇ Instalar Dependências", C_ACCENT, "#c0392b", self._do_install_deps, "btn3_install")])
            if self.is_silent:
                self.after(500, self._do_install_deps)

    def _do_install_deps(self):
        self.btn3_install.configure(state="disabled", text="⏳ Instalando (pode demorar)...")
        self.bar3.set(0)
        self.bar3.configure(mode="indeterminate")
        self.bar3.start()

        def worker():
            try:
                venv_dir = self.install_dir / "venv_ui"
                venv_python = venv_dir / "Scripts" / "python.exe"

                if not venv_python.exists():
                    self._log(self.log3, "▶ Criando ambiente da interface (venv_ui)...")
                    subprocess.run(["py", "-3.12", "-m", "venv", str(venv_dir)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

                req = self.install_dir / "requirements.txt"
                if not req.exists():
                    self._log(self.log3, "  Aviso: requirements.txt recriado localmente.")
                    req.write_text("Pillow>=10.0\nnatsort>=8.4\nrequests>=2.31\ncustomtkinter")

                self._log(self.log3, "▶ Instalando pacotes base no venv_ui...")
                proc = subprocess.run(
                    [str(venv_python), "-m", "pip", "install", "-r", str(req)],
                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )

                self.bar3.stop()
                self.bar3.configure(mode="determinate")
                self.bar3.set(1.0)

                if proc.returncode == 0:
                    self._log(self.log3, "✅ Dependências instaladas com sucesso!")
                    self.bar3.configure(progress_color=C_GREEN)
                    self.after(0, lambda: self.btn3_install.configure(text="✅ Próximo →", fg_color=C_GREEN, state="normal", command=self._run_step_4))
                    if self.is_silent:
                        self.after(500, self._run_step_4)
                else:
                    self._log(self.log3, f"❌ Erro na instalação:\n{proc.stderr}")
                    self.after(0, lambda: self.btn3_install.configure(text="Tentar Novamente", state="normal"))
            except Exception as e:
                self.bar3.stop()
                self.bar3.configure(mode="determinate")
                self._log(self.log3, f"❌ Erro: {e}")
                self.after(0, lambda: self.btn3_install.configure(text="Tentar Novamente", state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================
    # PASSO 4 - Concluir
    # =========================================================
    def _run_step_4(self):
        self.current_step = 4
        self._update_sidebar()
        self._clear_content()
        self._header("Instalação Concluída! 🎉", "O Manga AI Studio base foi configurado perfeitamente.")

        area = ctk.CTkFrame(self.content, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=36)

        ctk.CTkLabel(area, text="✅  Tudo pronto para usar", font=ctk.CTkFont(size=20, weight="bold"), text_color=C_GREEN).pack(pady=(20, 10))

        ctk.CTkLabel(area, text="Os módulos pesados de IA (OCR, CUDA) poderão ser instalados "
                                "diretamente \nde dentro do aplicativo usando a aba 'Central de Módulos'.",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED, justify="center").pack(pady=(0, 20))

        opts_frame = ctk.CTkFrame(area, fg_color="transparent")
        opts_frame.pack()

        self.var_shortcut = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_frame, text="Criar atalho na Área de Trabalho", variable=self.var_shortcut, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=6)

        self.var_open = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_frame, text="Iniciar Manga AI Studio agora", variable=self.var_open, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=6)

        self._footer_buttons(buttons_right=[("Concluir e Fechar", C_ACCENT, "#c0392b", self._finish, None)])
        if self.is_silent:
            self.after(1500, self._finish)

    def _finish(self):
        venv_pythonw = self.install_dir / "venv_ui" / "Scripts" / "pythonw.exe"
        app_py = self.install_dir / "app.py"

        if self.var_shortcut.get():
            icon = self.install_dir / "icon.ico"
            create_shortcut(target=venv_pythonw, name="Manga AI Studio", icon=icon, arguments=str(app_py), working_dir=self.install_dir)
            
        if self.var_open.get() and venv_pythonw.exists():
            subprocess.Popen([str(venv_pythonw), str(app_py)], cwd=str(self.install_dir), creationflags=subprocess.CREATE_NO_WINDOW)
            
        self.destroy()

if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
