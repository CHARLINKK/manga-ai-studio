import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import subprocess
import threading
import sys
import os
from pathlib import Path
from PIL import Image, ImageTk

# Configuração visual do tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_DIR = Path(os.getenv('LOCALAPPDATA')) / "MangaAIStudio"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
GLOBAL_DICT_PATH = CONFIG_DIR / "dicionario_global.txt"
LOCAL_DICT_PATH = CONFIG_DIR / "temp_dict_local.txt"
MODEL_PREFS_PATH = CONFIG_DIR / "model_prefs.json"

class RedirectText:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, string):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", string)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def flush(self):
        pass

class DraggableBlock(ctk.CTkFrame):
    def __init__(self, master, text_content, parent_app, original_text="", **kwargs):
        super().__init__(master, **kwargs)
        self.parent_app = parent_app
        self.original_text = original_text
        
        self.handle = ctk.CTkLabel(self, text="≡", cursor="fleur", font=ctk.CTkFont(size=20, weight="bold"), width=30)
        self.handle.pack(side="left", fill="y", padx=(5, 0))
        
        # Calculate dynamic height based on lines and word wrapping
        chars_per_line = 45 # estimativa segura
        estimated_lines = max(1, len(text_content) // chars_per_line) + text_content.count('\n')
        height = max(50, estimated_lines * 22 + 20)
        
        # Botão de exclusão
        self.btn_delete = ctk.CTkButton(self, text="X", width=24, height=height, fg_color="#C62828", hover_color="#B71C1C", command=self.on_delete)
        self.btn_delete.pack(side="right", padx=(0, 5), pady=5)
        
        self.textbox = ctk.CTkTextbox(self, height=height, font=ctk.CTkFont(size=14))
        self.textbox.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        try:
            self.textbox._textbox.configure(undo=True, maxundo=50)
        except:
            pass
        self.textbox.insert("end", text_content)
        
        self.handle.bind("<ButtonPress-1>", self.on_start)
        self.handle.bind("<B1-Motion>", self.on_drag)
        self.handle.bind("<ButtonRelease-1>", self.on_stop)
        
        self.on_focus_callback = None
        self.textbox.bind("<FocusIn>", self._handle_focus)

    def set_on_focus(self, callback):
        self.on_focus_callback = callback

    def _handle_focus(self, event):
        if self.on_focus_callback:
            self.on_focus_callback()

    def on_delete(self):
        self.parent_app.delete_block(self)

    def on_start(self, event):
        self.parent_app.start_block_drag(self, event)
        
    def on_drag(self, event):
        self.parent_app.do_block_drag(self, event)
        
    def on_stop(self, event):
        self.parent_app.stop_block_drag(self, event)

class MangaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Limpeza de pastas de atualização antigas
        try:
            import tempfile
            import shutil
            old_update_dir = Path(tempfile.gettempdir()) / "MangaAIStudio_Update"
            if old_update_dir.exists():
                shutil.rmtree(old_update_dir, ignore_errors=True)
        except Exception:
            pass

        self.title("Manga AI Studio")
        self.geometry("900x750")
        self.minsize(800, 600)
        # Permite maximizar/redimensionar a janela
        self.resizable(True, True)
        
        # Inicia maximizado no Windows
        try:
            self.after(200, lambda: self.state('zoomed'))
        except Exception:
            pass
        
        # Força o Windows a usar o ícone nativo na barra de tarefas
        import ctypes
        import sys
        import os
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("manga.ai.studio")
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # Frame principal para dividir Sidebar e Conteúdo
        self.root_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.root_frame.pack(fill="both", expand=True)

        # Barra Lateral (Workspace Explorer)
        self.sidebar_frame = ctk.CTkFrame(self.root_frame, width=250, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        
        self.label_workspace = ctk.CTkLabel(self.sidebar_frame, text="EXPLORADOR", font=ctk.CTkFont(size=14, weight="bold"))
        self.label_workspace.pack(pady=(10, 0), padx=10, anchor="w")
        
        self.btn_set_workspace = ctk.CTkButton(self.sidebar_frame, text="📂 Definir Pasta Base", fg_color="#444", hover_color="#555", command=self.set_workspace)
        self.btn_set_workspace.pack(pady=(10, 5), padx=10, fill="x")
        
        header_actions = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        header_actions.pack(fill="x", padx=10, pady=(0, 5))
        
        self.btn_refresh = ctk.CTkButton(header_actions, text="🔄", width=30, fg_color="#444", hover_color="#555", command=self.refresh_workspace)
        self.btn_refresh.pack(side="left", padx=(0, 5))
        
        self.btn_queue = ctk.CTkButton(header_actions, text="▶ Processar Fila", fg_color="#2b7a4b", hover_color="#3c9d64", command=self.action_process_queue)
        self.btn_queue.pack(side="left", fill="x", expand=True)
        
        self.workspace_checkboxes = {}
        
        self.workspace_list = ctk.CTkScrollableFrame(self.sidebar_frame, width=230, fg_color="transparent")
        self.workspace_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Área Principal (Abas)
        self.main_content_frame = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        self.main_content_frame.pack(side="right", fill="both", expand=True)

        # Título
        self.label_title = ctk.CTkLabel(self.main_content_frame, text="📖 Manga AI Studio", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_title.pack(pady=(10, 5))
        
        # Criando as Abas (Tabs)
        self.tabview = ctk.CTkTabview(self.main_content_frame)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Config do Workspace
        self.workspace_path = None
        self.workspace_config_file = CONFIG_DIR / "workspace.txt"
        self.load_workspace_config()
        
        self.tab_process = self.tabview.add("Processamento")
        self.tab_studio = self.tabview.add("Estúdio de Tradução")
        self.tab_reader = self.tabview.add("Leitor")
        self.tab_modules = self.tabview.add("Central de Módulos")

        self.setup_process_tab()
        self.setup_studio_tab()
        self.setup_reader_tab()
        self.setup_modules_tab()

    def set_workspace(self):
        path = filedialog.askdirectory(title="Selecione a Pasta Mãe dos Projetos")
        if path:
            self.workspace_path = Path(path)
            with open(self.workspace_config_file, "w", encoding="utf-8") as f:
                f.write(str(self.workspace_path))
            self.refresh_workspace()

    def load_workspace_config(self):
        if self.workspace_config_file.exists():
            with open(self.workspace_config_file, "r", encoding="utf-8") as f:
                path = f.read().strip()
                if path and os.path.isdir(path):
                    self.workspace_path = Path(path)
                    self.refresh_workspace()

    def refresh_workspace(self):
        for widget in self.workspace_list.winfo_children():
            widget.destroy()
            
        if not self.workspace_path or not self.workspace_path.exists():
            return
            
        # Lista as pastas filhas diretamente
        for child in self.workspace_path.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                self.create_workspace_item(child)

    def create_workspace_item(self, folder_path):
        frame = ctk.CTkFrame(self.workspace_list, fg_color="#333", corner_radius=5)
        frame.pack(fill="x", pady=5, padx=5)
        
        # Lógica de Status (Semáforo) — lê o status.json da Temp
        temp_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca" / "Temp"
        status_file = temp_dir / "status.json"
        
        base_name = folder_path.name
        folder_key = base_name
        
        status_color = "#e74c3c"  # Vermelho (padrão: sem processamento)
        if status_file.exists():
            try:
                import json
                with open(status_file, "r", encoding="utf-8") as f:
                    all_status = json.load(f)
                st = all_status.get(folder_key, {})
                if st.get("traduzido"):
                    status_color = "#2ecc71"  # Verde
                elif st.get("corrigido") or st.get("raw"):
                    status_color = "#f1c40f"  # Amarelo
            except Exception:
                pass
            
        header_frame = ctk.CTkFrame(frame, fg_color="#333")
        header_frame.pack(fill="x", padx=10, pady=(5, 5))
        
        # Checkbox para a Fila
        var_chk = ctk.BooleanVar(value=False)
        self.workspace_checkboxes[str(folder_path)] = var_chk
        chk = ctk.CTkCheckBox(header_frame, text="", variable=var_chk, width=20, checkbox_width=16, checkbox_height=16, bg_color="#333")
        chk.pack(side="left", padx=(0, 5))
        
        lbl_status = ctk.CTkLabel(header_frame, text="●", text_color=status_color, font=ctk.CTkFont(size=14), bg_color="#333")
        lbl_status.pack(side="left", padx=(0, 5))
        
        lbl = ctk.CTkLabel(header_frame, text=folder_path.name, font=ctk.CTkFont(weight="bold"), anchor="w", justify="left", bg_color="#333")
        lbl.pack(side="left", fill="x", expand=True, anchor="w")
        
        btn_frame = ctk.CTkFrame(frame, fg_color="#333")
        btn_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        btn_proc = ctk.CTkButton(btn_frame, text="▶ Processar", width=40, font=ctk.CTkFont(size=11), command=lambda p=folder_path: self.action_process_workspace(p))
        btn_proc.pack(side="left", fill="x", expand=True, padx=2)
        
        btn_edit = ctk.CTkButton(btn_frame, text="👁 Editor", width=40, font=ctk.CTkFont(size=11), command=lambda p=folder_path: self.action_editor_workspace(p))
        btn_edit.pack(side="left", fill="x", expand=True, padx=2)
        
        btn_studio = ctk.CTkButton(btn_frame, text="🌍 Estúdio", width=40, font=ctk.CTkFont(size=11), command=lambda p=folder_path: self.action_studio_workspace(p))
        btn_studio.pack(side="left", fill="x", expand=True, padx=2)
        
        # Clicar no nome do capítulo ainda recolhe/expande os botões
        def toggle_frame(event=None):
            if btn_frame.winfo_ismapped():
                btn_frame.pack_forget()
            else:
                btn_frame.pack(fill="x", padx=5, pady=(0, 5))
                
        lbl.bind("<Button-1>", toggle_frame)



    def repack_studio_blocks(self):
        for b in self.studio_blocks:
            if isinstance(b, DraggableBlock):
                b.pack_forget()
                b.pack(fill="x", pady=2)
            else:
                b.pack_forget()
                b.pack(fill="x", pady=2)

    def action_process_queue(self):
        selected = [p for p, var in self.workspace_checkboxes.items() if var.get()]
        if not selected:
            self.tabview.set("Processamento")
            self.log("\n⚠️ Fila Vazia: Marque pelo menos um capítulo para processar.")
            return
            
        self.tabview.set("Processamento")
        self.log(f"\n📦 INICIANDO FILA DE PROCESSAMENTO GLOBAL ({len(selected)} itens)")
        
        # Desabilita botões
        self.btn_run.configure(state="disabled", text="⏳ PROCESSANDO FILA...")
        self.btn_cancel.configure(state="normal", text="⏹ CANCELAR")
        self.progress_bar.set(0)
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("0.0", "end")
        self.textbox_log.configure(state="disabled")
        
        out_path = self.entry_output.get().strip()

        run_ocr = self.var_ocr.get()
        run_correct = self.var_correct.get()
        run_translate = self.var_translate.get()
        
        # Validação Modular
        if run_ocr and not self.check_module_ocr():
            self.log("⚠️ ATENÇÃO: O Motor OCR não está instalado.")
            self.log("Vá até a aba 'Central de Módulos' e instale-o antes de usar a Etapa 1.")
            self.tabview.set("Central de Módulos")
            return
            
        if (run_correct or run_translate) and not self.check_module_translation():
            self.log("⚠️ ATENÇÃO: O Motor de Tradução (IA) não está instalado.")
            self.log("Vá até a aba 'Central de Módulos' e instale-o antes de usar as Etapas 2 e 3.")
            self.tabview.set("Central de Módulos")
            return

        dict_global = self.textbox_dict_global.get("0.0", "end").strip()
        dict_local = self.textbox_dict.get("0.0", "end").strip()
        bilingual = self.var_bilingual.get()
        pause_ocr = self.var_pause_ocr.get()

        def queue_thread():
            for i, p in enumerate(selected):
                self.log(f"\n\n==================================================")
                self.log(f"📦 ITEM {i+1}/{len(selected)} DA FILA: {Path(p).name}")
                self.log(f"==================================================")
                self.process_pipeline(p, out_path, run_ocr, run_correct, run_translate, dict_global, dict_local, bilingual, pause_ocr)
                
            self.log("\n✅✅ FILA DE PROCESSAMENTO CONCLUÍDA! ✅✅")
            self.after(0, self.refresh_workspace)
            
            # Reabilita botões
            self.after(0, lambda: self.btn_run.configure(state="normal", text="▶ INICIAR PROCESSAMENTO"))
            self.after(0, lambda: self.btn_cancel.configure(state="disabled", text="⏹ CANCELAR"))

        threading.Thread(target=queue_thread, daemon=True).start()

    def action_process_workspace(self, folder_path):
        self.tabview.set("Processamento")
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, str(folder_path))
        self.log(f"\n📂 Projeto '{folder_path.name}' selecionado para Processamento.")

    def _find_newest_txt_for_workspace(self, folder_path, valid_suffixes):
        """Busca genérica usada pela auto-mesclagem no pipeline. Procura APENAS na Temp."""
        temp_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca" / "Temp"
        base_name = folder_path.name
        candidates = []
        
        # Procura na pasta Temp pelo nome da pasta-mãe da imagem
        for suffix in valid_suffixes:
            f = temp_dir / f"{base_name}{suffix}"
            if f.exists():
                candidates.append(f)
                
        if not candidates:
            return None
            
        # Ordena do mais recente para o mais antigo
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]

    def _find_txt_in_temp(self, folder_path, valid_suffixes):
        """Procura APENAS na Temp por arquivos com os sufixos válidos para esta pasta."""
        temp_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca" / "Temp"
        base_name = Path(folder_path).name
        candidates = []
        
        for suffix in valid_suffixes:
            f = temp_dir / f"{base_name}{suffix}"
            if f.exists():
                candidates.append(f)
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]

    def _find_txt_in_biblioteca(self, folder_path):
        """Procura na Biblioteca Central por arquivos finalizados desta pasta."""
        biblioteca_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca"
        base_name = Path(folder_path).name
        candidates = []
        
        try:
            for f in biblioteca_dir.iterdir():
                if f.is_file() and f.suffix.lower() == ".txt" and not f.parent.name == "Temp":
                    candidates.append(f)
        except Exception:
            pass
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]

    def action_editor_workspace(self, folder_path):
        """Editor: puxa _raw.txt ou _corrigido.txt da Temp."""
        target = self._find_txt_in_temp(folder_path, ["_corrigido.txt", "_corrected.txt", "_raw.txt"])
        
        if target:
            self.load_studio_from_pipeline(str(folder_path), str(target), is_editor_mode=True)
        else:
            self.log(f"⚠️ Nenhum texto OCR encontrado na Temp para esta pasta. Extraia o texto primeiro.")
            self.tabview.set("Processamento")
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, str(folder_path))

    def action_studio_workspace(self, folder_path):
        """Studio: puxa _traduzido.txt da Temp."""
        target = self._find_txt_in_temp(folder_path, ["_traduzido.txt", "_translated.txt"])
        
        if target:
            self.load_studio_from_pipeline(str(folder_path), str(target), is_editor_mode=False)
        else:
            self.log(f"⚠️ Nenhum texto traduzido encontrado na Temp. Processe a tradução primeiro.")
            self.tabview.set("Processamento")
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, str(folder_path))

    def setup_process_tab(self):
        self.scroll_process = ctk.CTkScrollableFrame(self.tab_process, fg_color="transparent")
        self.scroll_process.pack(fill="both", expand=True)

        # Frame de Arquivo
        self.frame_file = ctk.CTkFrame(self.scroll_process)
        self.frame_file.pack(fill="x", padx=10, pady=10)

        self.label_file = ctk.CTkLabel(self.frame_file, text="Pasta ou Arquivo:")
        self.label_file.pack(side="left", padx=10, pady=10)

        self.entry_path = ctk.CTkEntry(self.frame_file, placeholder_text="Caminho da imagem ou da pasta do capítulo...")
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        self.btn_browse = ctk.CTkButton(self.frame_file, text="Procurar...", width=100, command=self.browse_path)
        self.btn_browse.pack(side="right", padx=10, pady=10)

        # Frame de Saída
        self.frame_output = ctk.CTkFrame(self.scroll_process)
        self.frame_output.pack(fill="x", padx=10, pady=(0, 10))

        self.label_output = ctk.CTkLabel(self.frame_output, text="Pasta de Saída:")
        self.label_output.pack(side="left", padx=10, pady=10)

        self.entry_output = ctk.CTkEntry(self.frame_output, placeholder_text="Opcional. Se vazio, salva ao lado da original.")
        self.entry_output.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        self.btn_browse_output = ctk.CTkButton(self.frame_output, text="Procurar...", width=100, command=self.browse_output_path)
        self.btn_browse_output.pack(side="right", padx=10, pady=10)

        # Dividindo Configurações em Duas Colunas
        self.frame_configs = ctk.CTkFrame(self.scroll_process, fg_color="transparent")
        self.frame_configs.pack(fill="both", expand=True, padx=10, pady=5)

        # Coluna Esquerda: Etapas
        self.frame_opts = ctk.CTkFrame(self.frame_configs)
        self.frame_opts.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.label_opts = ctk.CTkLabel(self.frame_opts, text="Etapas de Processamento:", font=ctk.CTkFont(weight="bold"))
        self.label_opts.pack(anchor="w", padx=10, pady=(10, 5))

        self.var_ocr = ctk.BooleanVar(value=True)
        self.cb_ocr = ctk.CTkCheckBox(self.frame_opts, text="1. Extrair Texto Bruto (GPU)", variable=self.var_ocr)
        self.cb_ocr.pack(anchor="w", padx=20, pady=5)
        
        self.var_pause_ocr = ctk.BooleanVar(value=False)
        self.cb_pause_ocr = ctk.CTkCheckBox(self.frame_opts, text="↳ Pausar após OCR (Ir para Editor Visual)", variable=self.var_pause_ocr)
        self.cb_pause_ocr.pack(anchor="w", padx=45, pady=0)

        self.var_correct = ctk.BooleanVar(value=True)
        self.cb_correct = ctk.CTkCheckBox(self.frame_opts, text="2. Polir Inglês 99.9% (Llama 3.1 GPU)", variable=self.var_correct)
        self.cb_correct.pack(anchor="w", padx=20, pady=5)

        self.var_translate = ctk.BooleanVar(value=False)
        self.cb_translate = ctk.CTkCheckBox(self.frame_opts, text="3. Traduzir para PT-BR (Llama 3.1 GPU)", variable=self.var_translate)
        self.cb_translate.pack(anchor="w", padx=20, pady=5)

        self.var_bilingual = ctk.BooleanVar(value=False)
        self.cb_bilingual = ctk.CTkCheckBox(self.frame_opts, text="↳ Exportar Formato Bilíngue [EN/PTBR]", variable=self.var_bilingual)
        self.cb_bilingual.pack(anchor="w", padx=45, pady=0)
        
        self.var_pause_translate = ctk.BooleanVar(value=False)
        self.cb_pause_translate = ctk.CTkCheckBox(self.frame_opts, text="↳ Pausar após Tradução (Ir para Estúdio)", variable=self.var_pause_translate)
        self.cb_pause_translate.pack(anchor="w", padx=45, pady=5)
        
        # (Seletor de modelo movido para a aba de Módulos)

        
        # Tone Selection for Translation
        self.label_tone = ctk.CTkLabel(self.frame_opts, text="Tom da Tradução:")
        self.label_tone.pack(anchor="w", padx=20, pady=(10, 0))
        self.combo_tone = ctk.CTkComboBox(self.frame_opts, values=["Formal", "Neutro", "Informal"])
        self.combo_tone.set("Neutro")
        self.combo_tone.pack(anchor="w", padx=20, pady=(0, 5))
        
        # Switch RAG Memory (Moved to Modules tab, just declare var here)
        self.var_use_rag = ctk.BooleanVar(value=True)

        # Coluna Direita: Dicionários
        self.frame_dicts = ctk.CTkFrame(self.frame_configs)
        self.frame_dicts.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.label_dict_global = ctk.CTkLabel(self.frame_dicts, text="Dicionário Global Permanente:", font=ctk.CTkFont(weight="bold"))
        self.label_dict_global.pack(anchor="w", padx=10, pady=(10, 0))
        self.entry_dict_global = ctk.CTkTextbox(self.frame_dicts, height=60)
        self.entry_dict_global.pack(fill="x", padx=10, pady=5)
        # Carrega dicionário global se existir
        if GLOBAL_DICT_PATH.exists():
            with open(GLOBAL_DICT_PATH, "r", encoding="utf-8") as f:
                self.entry_dict_global.insert("end", f.read())
        else:
            self.entry_dict_global.insert("end", "Macho Cooksan = Macho Cooksan\n")

        self.label_dict_local = ctk.CTkLabel(self.frame_dicts, text="Dicionário Temporário (Exclusivo da fila atual):", font=ctk.CTkFont(weight="bold"))
        self.label_dict_local.pack(anchor="w", padx=10, pady=(5, 0))
        self.entry_dict_local = ctk.CTkTextbox(self.frame_dicts, height=60)
        self.entry_dict_local.pack(fill="x", padx=10, pady=5)

        # Avisos discretos de Status (GPU e RAG)
        self.frame_discreet_status = ctk.CTkFrame(self.scroll_process, fg_color="transparent")
        self.frame_discreet_status.pack(fill="x", padx=10, pady=(0, 5))
        
        self.lbl_process_status_cuda = ctk.CTkLabel(self.frame_discreet_status, text="GPU: ⏳ Verificando...", font=ctk.CTkFont(size=11), text_color="#aaa")
        self.lbl_process_status_cuda.pack(side="left", padx=10)
        
        self.lbl_process_status_rag = ctk.CTkLabel(self.frame_discreet_status, text="RAG: ⏳ Verificando...", font=ctk.CTkFont(size=11), text_color="#aaa")
        self.lbl_process_status_rag.pack(side="left", padx=10)

        # Botões Iniciar/Cancelar
        self.frame_buttons = ctk.CTkFrame(self.scroll_process, fg_color="transparent")
        self.frame_buttons.pack(fill="x", padx=10, pady=(10, 5))

        self.btn_run = ctk.CTkButton(self.frame_buttons, text="▶ INICIAR PROCESSAMENTO", height=45, font=ctk.CTkFont(size=15, weight="bold"), command=self.start_processing)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(self.frame_buttons, text="⏹ CANCELAR", height=45, width=130, font=ctk.CTkFont(size=15, weight="bold"), fg_color="#c0392b", hover_color="#e74c3c", command=self.cancel_processing, state="disabled")
        self.btn_cancel.pack(side="right")

        self.btn_reset_process = ctk.CTkButton(self.frame_buttons, text="🗑 Limpar", height=45, width=100, fg_color="#555", hover_color="#777", command=self.reset_processing_tab)
        self.btn_reset_process.pack(side="right", padx=(0, 10))

        # Progresso
        self.frame_progress = ctk.CTkFrame(self.scroll_process, fg_color="transparent")
        self.frame_progress.pack(fill="x", padx=10, pady=(10, 0))
        
        self.lbl_current_step = ctk.CTkLabel(self.frame_progress, text="", font=ctk.CTkFont(weight="bold", size=14), text_color="#f1c40f")
        self.lbl_current_step.pack(pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.frame_progress, height=12)
        self.progress_bar.pack(fill="x", padx=10, pady=(5, 10))
        self.progress_bar.set(0)

        # Console (Log)
        self.textbox_log = ctk.CTkTextbox(self.scroll_process, height=120, state="disabled", font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))



    def setup_studio_tab(self):
        # Frame principal do Estúdio
        self.frame_studio_main = ctk.CTkFrame(self.tab_studio, fg_color="transparent")
        self.frame_studio_main.pack(fill="both", expand=True, padx=0, pady=0)

        # Barra de ferramentas
        self.frame_studio_toolbar = ctk.CTkFrame(self.frame_studio_main, fg_color="#183A28", corner_radius=8)
        self.frame_studio_toolbar.pack(fill="x", pady=(0, 10), padx=5)

        self.lbl_studio_title = ctk.CTkLabel(self.frame_studio_toolbar, text="🎙️ ESTÚDIO DE TRADUÇÃO", font=ctk.CTkFont(size=15, weight="bold"), text_color="#77CC99", width=250, anchor="w")
        self.lbl_studio_title.pack(side="left", padx=15, pady=10)

        self.btn_clear_studio = ctk.CTkButton(self.frame_studio_toolbar, text="🗑 Limpar Estúdio", fg_color="#2A503C", hover_color="#1E3E2D", command=self.reset_studio_tab)
        self.btn_clear_studio.pack(side="left", padx=(10, 0), pady=10)

        self.btn_save_continue = ctk.CTkButton(self.frame_studio_toolbar, text="🚀 Salvar e Continuar Processamento", fg_color="#d35400", hover_color="#a84300", command=self.save_and_continue)
        self.btn_save_continue.pack(side="right", padx=(10, 10), pady=10)
        self.btn_save_continue.pack_forget() # Hidden by default
        
        self.btn_save_studio = ctk.CTkButton(self.frame_studio_toolbar, text="💾 Salvar Tradução", fg_color="#27ae60", hover_color="#2ecc71", command=self.save_studio_text)
        self.btn_save_studio.pack(side="right", padx=(10, 10), pady=10)

        # Divisão em três áreas
        self.frame_studio_split = ctk.CTkFrame(self.frame_studio_main, fg_color="transparent")
        self.frame_studio_split.pack(fill="both", expand=True)

        # Painel Lateral (Páginas)
        self.frame_studio_pages = ctk.CTkScrollableFrame(self.frame_studio_split, width=150)
        self.frame_studio_pages.pack(side="left", fill="y", padx=(0, 5))
        
        self.studio_pages_original = {}
        self.studio_pages_translated = {}
        self.studio_images_paths = {}
        self.studio_current_page = None
        self.studio_translated_txt_path = None

        # Painel Imagem (Meio) - Usando Canvas para Pan e Zoom com Mouse
        self.frame_studio_img = ctk.CTkFrame(self.frame_studio_split)
        self.frame_studio_img.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.lbl_studio_page_info = ctk.CTkLabel(self.frame_studio_img, text="", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.lbl_studio_page_info.pack(side="top", pady=(5, 0))
        
        self.canvas_studio_img = tk.Canvas(self.frame_studio_img, bg="#2b2b2b", highlightthickness=0)
        self.canvas_studio_img.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.studio_original_pil_image = None
        self.studio_zoom_level = 1.0
        self.studio_img_id = None
        self.studio_img_x = 0
        self.studio_img_y = 0
        self.studio_drag_start_x = 0
        self.studio_drag_start_y = 0
        self.studio_current_tk_image = None

        self.canvas_studio_img.bind("<MouseWheel>", self.on_studio_mouse_wheel)
        self.canvas_studio_img.bind("<ButtonPress-1>", self.on_studio_drag_start)
        self.canvas_studio_img.bind("<B1-Motion>", self.on_studio_drag_motion)

        # Atalhos do Estúdio
        self.bind("<Control-s>", lambda e: self.save_studio_text() if self.tabview.get() == "Estúdio de Tradução" else None)
        self.bind("<Left>", lambda e: self.navigate_studio_page(-1) if self.tabview.get() == "Estúdio de Tradução" else None)
        self.bind("<Right>", lambda e: self.navigate_studio_page(1) if self.tabview.get() == "Estúdio de Tradução" else None)
        self.bind("<Up>", lambda e: self.navigate_studio_page(-1) if self.tabview.get() == "Estúdio de Tradução" else None)
        self.bind("<Down>", lambda e: self.navigate_studio_page(1) if self.tabview.get() == "Estúdio de Tradução" else None)

        # Painel Texto (Direita)
        self.frame_studio_txt = ctk.CTkFrame(self.frame_studio_split)
        self.frame_studio_txt.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.label_studio_original = ctk.CTkLabel(self.frame_studio_txt, text="Texto Original do Bloco Selecionado:", font=ctk.CTkFont(weight="bold"))
        self.label_studio_original.pack(anchor="w", padx=5, pady=(5, 0))
        
        self.textbox_studio_original = ctk.CTkTextbox(self.frame_studio_txt, height=80, font=ctk.CTkFont(size=14), fg_color="#333", text_color="#ccc")
        self.textbox_studio_original.pack(fill="x", padx=5, pady=(0, 10))
        self.textbox_studio_original.insert("0.0", "Selecione um bloco de tradução abaixo para ver o original...")
        self.textbox_studio_original.configure(state="disabled")
        
        self.label_studio_translated = ctk.CTkLabel(self.frame_studio_txt, text="Tradução:", font=ctk.CTkFont(weight="bold"))
        self.label_studio_translated.pack(anchor="w", padx=5, pady=(0, 0))
        
        self.frame_studio_blocks = ctk.CTkScrollableFrame(self.frame_studio_txt)
        self.frame_studio_blocks.pack(fill="both", expand=True, padx=5, pady=5)
        self.studio_blocks = []
        
        self.btn_studio_add_block = ctk.CTkButton(self.frame_studio_txt, text="+ Adicionar Bloco de Texto", fg_color="#2E7D32", hover_color="#1B5E20", command=lambda: self._create_studio_block(""))
        self.btn_studio_add_block.pack(fill="x", padx=5, pady=(0, 10))
        
        self.label_studio_dict = ctk.CTkLabel(self.frame_studio_txt, text="Dicionário Temporário (Adicione termos aqui):", font=ctk.CTkFont(weight="bold"))
        self.label_studio_dict.pack(anchor="w", padx=5, pady=(5, 0))
        
        self.textbox_studio_dict = ctk.CTkTextbox(self.frame_studio_txt, font=ctk.CTkFont(size=14), height=100)
        self.textbox_studio_dict.pack(fill="x", padx=5, pady=(0, 10))
        
        self.studio_is_editor_mode = False

    def on_studio_mouse_wheel(self, event):
        if not self.studio_original_pil_image:
            return
        if event.delta > 0:
            self.studio_zoom_level += 0.1
        else:
            self.studio_zoom_level = max(0.1, self.studio_zoom_level - 0.1)
        self.update_studio_image()

    def on_studio_drag_start(self, event):
        self.studio_drag_start_x = event.x
        self.studio_drag_start_y = event.y

    def apply_studio_bounds(self):
        if not hasattr(self, 'studio_current_img_w'): return
        self.update_idletasks()
        cw = self.canvas_studio_img.winfo_width()
        ch = self.canvas_studio_img.winfo_height()
        
        if self.studio_current_img_w > cw:
            min_x = cw - self.studio_current_img_w / 2
            max_x = self.studio_current_img_w / 2
        else:
            min_x = self.studio_current_img_w / 2
            max_x = cw - self.studio_current_img_w / 2
            
        if self.studio_img_x < min_x: self.studio_img_x = min_x
        if self.studio_img_x > max_x: self.studio_img_x = max_x
        
        if self.studio_current_img_h > ch:
            min_y = ch - self.studio_current_img_h / 2
            max_y = self.studio_current_img_h / 2
        else:
            min_y = self.studio_current_img_h / 2
            max_y = ch - self.studio_current_img_h / 2
            
        if self.studio_img_y < min_y: self.studio_img_y = min_y
        if self.studio_img_y > max_y: self.studio_img_y = max_y

    def on_studio_drag_motion(self, event):
        if not self.studio_original_pil_image or not self.studio_img_id:
            return
            
        dx = event.x - self.studio_drag_start_x
        dy = event.y - self.studio_drag_start_y
        
        old_x, old_y = self.studio_img_x, self.studio_img_y
        self.studio_img_x += dx
        self.studio_img_y += dy
        
        self.apply_studio_bounds()
        
        actual_dx = self.studio_img_x - old_x
        actual_dy = self.studio_img_y - old_y
        
        self.canvas_studio_img.move(self.studio_img_id, actual_dx, actual_dy)
        self.studio_drag_start_x = event.x
        self.studio_drag_start_y = event.y

    def update_studio_image(self):
        if not self.studio_original_pil_image:
            return
            
        img = self.studio_original_pil_image
        base_ratio = 800.0 / img.height
        new_w = int(img.width * base_ratio * self.studio_zoom_level)
        new_h = int(img.height * base_ratio * self.studio_zoom_level)
        
        if new_w <= 0 or new_h <= 0: return
        
        self.studio_current_img_w = new_w
        self.studio_current_img_h = new_h
        
        img_resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        new_tk_image = ImageTk.PhotoImage(img_resized)
        
        self.apply_studio_bounds()
        
        if self.studio_img_id:
            self.canvas_studio_img.itemconfig(self.studio_img_id, image=new_tk_image)
            self.canvas_studio_img.coords(self.studio_img_id, self.studio_img_x, self.studio_img_y)
        else:
            self.studio_img_id = self.canvas_studio_img.create_image(self.studio_img_x, self.studio_img_y, image=new_tk_image, anchor="center")
            
        self.studio_current_tk_image = new_tk_image

    def _create_studio_block(self, text, original_text=""):
        block = DraggableBlock(self.frame_studio_blocks, text, self, original_text=original_text)
        block.pack(fill="x", pady=2)
        self.studio_blocks.append(block)
        
        def on_focus():
            if getattr(self, 'studio_is_editor_mode', False):
                return
            self.textbox_studio_original.configure(state="normal")
            self.textbox_studio_original.delete("0.0", "end")
            if original_text:
                self.textbox_studio_original.insert("0.0", original_text)
            else:
                self.textbox_studio_original.insert("0.0", "(Sem texto original disponível para este bloco)")
            self.textbox_studio_original.configure(state="disabled")
            
        block.set_on_focus(on_focus)
        return block

    def delete_studio_block(self, block):
        if block in self.studio_blocks:
            self.studio_blocks.remove(block)
            block.destroy()


    def on_mouse_wheel(self, event):
        if not self.original_pil_image:
            return
        if event.delta > 0:
            self.zoom_level += 0.1
        else:
            self.zoom_level = max(0.1, self.zoom_level - 0.1)
            
        if hasattr(self, '_zoom_job') and self._zoom_job:
            self.canvas_img.after_cancel(self._zoom_job)
        self._zoom_job = self.canvas_img.after(30, self.update_editor_image)

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def apply_bounds(self):
        if not hasattr(self, 'current_img_w'): return
        
        self.update_idletasks() # garante dimensoes atualizadas
        cw = self.canvas_img.winfo_width()
        ch = self.canvas_img.winfo_height()
        
        if self.current_img_w > cw:
            min_x = cw - self.current_img_w / 2
            max_x = self.current_img_w / 2
        else:
            min_x = self.current_img_w / 2
            max_x = cw - self.current_img_w / 2
            
        if self.img_x < min_x: self.img_x = min_x
        if self.img_x > max_x: self.img_x = max_x
        
        if self.current_img_h > ch:
            min_y = ch - self.current_img_h / 2
            max_y = self.current_img_h / 2
        else:
            min_y = self.current_img_h / 2
            max_y = ch - self.current_img_h / 2
            
        if self.img_y < min_y: self.img_y = min_y
        if self.img_y > max_y: self.img_y = max_y

    def on_drag_motion(self, event):
        if not self.original_pil_image or not self.img_id:
            return
            
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        old_x, old_y = self.img_x, self.img_y
        self.img_x += dx
        self.img_y += dy
        
        self.apply_bounds()
        
        actual_dx = self.img_x - old_x
        actual_dy = self.img_y - old_y
        
        self.canvas_img.move(self.img_id, actual_dx, actual_dy)
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def load_editor_image(self):
        path = filedialog.askopenfilename(title="Selecionar Imagem do Mangá", filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")])
        if path:
            try:
                self.original_pil_image = Image.open(path)
                self.zoom_level = 1.0
                
                # Centraliza a imagem na primeira vez
                self.update_idletasks()
                self.img_x = self.canvas_img.winfo_width() / 2
                self.img_y = self.canvas_img.winfo_height() / 2
                
                self.update_editor_image()
            except Exception as e:
                self.textbox_editor.insert("end", f"Erro ao carregar imagem: {e}\n")
                
    def update_editor_image(self):
        if not self.original_pil_image:
            return
            
        img = self.original_pil_image
        base_ratio = 800.0 / img.height
        new_w = int(img.width * base_ratio * self.zoom_level)
        new_h = int(img.height * base_ratio * self.zoom_level)
        
        if new_w <= 0 or new_h <= 0: return
        
        self.current_img_w = new_w
        self.current_img_h = new_h
        
        # Alterado de LANCZOS para BILINEAR (muito mais rápido para evitar lag)
        img_resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        new_tk_image = ImageTk.PhotoImage(img_resized)
        
        self.apply_bounds()
        
        if self.img_id:
            # itemconfig substitui a imagem instantaneamente sem piscar (flicker)
            self.canvas_img.itemconfig(self.img_id, image=new_tk_image)
            self.canvas_img.coords(self.img_id, self.img_x, self.img_y)
        else:
            self.img_id = self.canvas_img.create_image(self.img_x, self.img_y, image=new_tk_image, anchor="center")
            
        self.current_tk_image = new_tk_image  # Segura a referência apenas AGORA, para a velha não ser apagada antes

    def load_studio_folder(self):
        folder_path = filedialog.askdirectory(title="Selecionar Pasta do Capítulo (Contendo imagens e txts)")
        if not folder_path: return
        self._load_studio_data(folder_path)

    def load_studio_from_pipeline(self, folder_path, txt_path, is_editor_mode=False):
        p = Path(folder_path)
        if p.is_file():
            p = p.parent
            
        folder_path = str(p)
        self.tabview.set("Estúdio de Tradução")
        self.update()
        self.update_idletasks()
        
        self.studio_is_editor_mode = is_editor_mode
        self._load_studio_data(folder_path, txt_path)

    def _parse_studio_txt(self, path):
        # Retorna dict de paginas -> lista de linhas. Suporta formato bilingue.
        import re
        pages_original = {}
        pages_translated = {}
        if not os.path.exists(path):
            return pages_original, pages_translated
            
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
                
        # Regex robusto que captura qualquer variante de "PÁGINA X: nome"
        # incluindo encodings corrompidos (P.GINA, PAGINA, PÁGINA, etc.)
        PAGE_RE = re.compile(r'^P.{0,2}GINA\s+\d+\s*:\s*(.+)$', re.IGNORECASE)
        
        current_page = None
        for line in content.split('\n'):
            ls = line.strip().rstrip('\r')
            m = PAGE_RE.match(ls)
            if m:
                current_page = m.group(1).strip()
                pages_original[current_page] = []
                pages_translated[current_page] = []
            elif current_page is not None and not ls.startswith("==="):
                if ls.upper().startswith("[EN]:"):
                    pages_original[current_page].append(ls[5:].strip())
                elif ls.upper().startswith("[BR]:"):
                    pages_translated[current_page].append(ls[5:].strip())
                else:
                    pages_original[current_page].append(ls)
                    pages_translated[current_page].append(ls)
                
        return pages_original, pages_translated

    def _load_studio_data(self, folder_path, txt_path=None):
        if not txt_path:
            # Fallback (caso carregado via botão "Abrir Pasta" no Estúdio)
            folder = Path(folder_path)
            txts = list(folder.rglob("*.txt"))
            translated_path = next((f for f in txts if "_traduzido" in f.name or "_translated" in f.name), None)
            corrected_path = next((f for f in txts if "_corrigido" in f.name or "_corrected" in f.name), None)
            raw_path = next((f for f in txts if "_raw" in f.name), None)
            
            if not translated_path:
                translated_path = corrected_path or raw_path
            
            if translated_path:
                txt_path = str(translated_path)
                
        if not txt_path or not os.path.exists(txt_path):
            self.log("⚠️ Nenhum arquivo de texto encontrado para o Estúdio.")
            return
        
        self.studio_translated_txt_path = txt_path
        
        # Ocultar/Mostrar componentes de acordo com o modo
        if getattr(self, 'studio_is_editor_mode', False):
            self.frame_studio_toolbar.configure(fg_color="#1B263B")
            self.lbl_studio_title.configure(text="✏️ EDITOR OCR", text_color="#88AADD")
            self.btn_save_continue.pack(side="right", padx=(10, 10), pady=10)
            self.btn_save_studio.configure(text="💾 Apenas Salvar")
            
            self.label_studio_original.configure(text="Referência (Desativado no OCR):")
            self.textbox_studio_original.configure(state="normal")
            self.textbox_studio_original.delete("0.0", "end")
            self.textbox_studio_original.insert("0.0", "Não aplicável no modo OCR...")
            self.textbox_studio_original.configure(state="disabled")
            
            self.label_studio_translated.configure(text="Texto OCR (Extraído):")
            
            self.textbox_studio_dict.configure(state="normal")
            self.textbox_studio_dict.delete("0.0", "end")
            self.textbox_studio_dict.insert("end", self.entry_dict_local.get("0.0", "end-1c"))
        else:
            self.frame_studio_toolbar.configure(fg_color="#183A28")
            self.lbl_studio_title.configure(text="🎙️ ESTÚDIO DE TRADUÇÃO", text_color="#77CC99")
            self.btn_save_continue.pack_forget()
            self.btn_save_studio.configure(text="💾 Salvar Tradução")
            
            self.label_studio_original.configure(text="Texto Original do Bloco Selecionado:")
            self.textbox_studio_original.configure(state="normal")
            self.textbox_studio_original.delete("0.0", "end")
            self.textbox_studio_original.insert("0.0", "Selecione um bloco de tradução abaixo para ver o original...")
            self.textbox_studio_original.configure(state="disabled")
            
            self.label_studio_translated.configure(text="Tradução:")
            
            self.textbox_studio_dict.configure(state="normal")
            self.textbox_studio_dict.delete("0.0", "end")
            self.textbox_studio_dict.insert("end", self.entry_dict_local.get("0.0", "end-1c"))
        
        # 1. Parse Original (pega o primeiro retorno: clean text ou a parte [EN])
        self.studio_pages_original, _ = self._parse_studio_txt(txt_path)
        # 2. Parse Traduzido (pega o segundo retorno: clean text ou a parte [BR])
        _, self.studio_pages_translated = self._parse_studio_txt(txt_path)
        
        # 3. Find images
        self.studio_images_paths = {}
        if os.path.isdir(folder_path):
            supported_formats = {'.png', '.jpg', '.jpeg', '.webp'}
            import re
            def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
                return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)]
                
            images = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in supported_formats]
            images = sorted(images, key=natural_sort_key)
            for img in images:
                self.studio_images_paths[img] = os.path.join(folder_path, img)
                
        # 4. Populate sidebar
        for widget in self.frame_studio_pages.winfo_children():
            widget.destroy()
            
        for img_name in self.studio_images_paths.keys():
            has_text = False
            if img_name in self.studio_pages_translated:
                if any(t.strip() for t in self.studio_pages_translated[img_name]):
                    has_text = True
                    
            if has_text:
                btn = ctk.CTkButton(self.frame_studio_pages, text=f"\u2705 {img_name}", fg_color="#27ae60", hover_color="#2ecc71", command=lambda n=img_name: self.select_studio_page(n))
            else:
                btn = ctk.CTkButton(self.frame_studio_pages, text=img_name, command=lambda n=img_name: self.select_studio_page(n))
            btn.pack(fill="x", pady=2)
            
        # Select first page
        if self.studio_images_paths:
            first = list(self.studio_images_paths.keys())[0]
            self.after(150, lambda: self.select_studio_page(first))

    def navigate_studio_page(self, direction):
        if not self.studio_images_paths: return
        keys = list(self.studio_images_paths.keys())
        if self.studio_current_page in keys:
            idx = keys.index(self.studio_current_page)
            new_idx = idx + direction
            if 0 <= new_idx < len(keys):
                self.select_studio_page(keys[new_idx])

    def select_studio_page(self, page_name):
        self.studio_current_page = page_name
        self.lbl_studio_page_info.configure(text=f"Página Aberta: {page_name}")
        
        for block in self.studio_blocks:
            block.destroy()
        self.studio_blocks = []
        
        # Load blocks for translated
        translated_lines = self.studio_pages_translated.get(page_name, [])
        original_lines = self.studio_pages_original.get(page_name, [])
        
        # Cria um bloco para cada separação de linha vazia
        import itertools
        def split_by_empty_lines(lines):
            return ["\n".join(group) for k, group in itertools.groupby(lines, key=bool) if k]
            
        t_blocks = split_by_empty_lines(translated_lines)
        o_blocks = split_by_empty_lines(original_lines)
        
        for i, text in enumerate(t_blocks):
            orig_text = o_blocks[i] if i < len(o_blocks) else ""
            self._create_studio_block(text, orig_text)
            
        # Load image
        img_path = self.studio_images_paths.get(page_name)
        if img_path and os.path.exists(img_path):
            try:
                self.studio_original_pil_image = Image.open(img_path)
                self.studio_zoom_level = 1.0
                self.update_idletasks()
                self.studio_img_x = self.canvas_studio_img.winfo_width() / 2
                self.studio_img_y = self.canvas_studio_img.winfo_height() / 2
                self.update_studio_image()
            except Exception as e:
                print(f"Erro ao carregar imagem no estudio: {e}")

    def save_studio_text(self):
        dialog = ctk.CTkInputDialog(text="Digite o nome final do arquivo para exportação (sem .txt):", title="Finalizar Tradução")
        nome_final = dialog.get_input()
        
        if not nome_final:
            self.log("⚠️ Exportação cancelada.")
            return
            
        nome_final = nome_final.strip()
        if not nome_final.endswith(".txt"):
            nome_final += ".txt"
        
        # Detecta automaticamente se o arquivo carregado era bilíngue
        # (se qualquer página tem texto original diferente do traduzido)
        bilingual_detected = False
        for page, orig_lines in self.studio_pages_original.items():
            trans_lines = self.studio_pages_translated.get(page, [])
            orig_flat = " ".join(l for l in orig_lines if l.strip())
            trans_flat = " ".join(l for l in trans_lines if l.strip())
            if orig_flat and orig_flat != trans_flat:
                bilingual_detected = True
                break
        
        # O checkbox da UI também pode forçar bilíngue mesmo se o arquivo original não era
        bilingual_enabled = bilingual_detected or self.var_bilingual.get()
        
        # Atualiza a memória com os blocos da página atual (editados pelo usuário)
        if self.studio_current_page:
            new_lines = []
            for block in self.studio_blocks:
                traducao = block.textbox.get("0.0", "end-1c").strip()
                if bilingual_enabled and block.original_text:
                    new_lines.append(f"[EN]: {block.original_text}")
                    new_lines.append(f"[BR]: {traducao}")
                else:
                    new_lines.append(traducao)
                new_lines.append("")  # separador
            self.studio_pages_translated[self.studio_current_page] = "\n".join(new_lines).split("\n")
            
        # Grava no arquivo final — para páginas não visitadas, reconstroe o formato bilíngue
        lines = []
        for page, trans_texts in self.studio_pages_translated.items():
            lines.append("=" * 50)
            lines.append(f"PÁGINA 1: {page}")
            lines.append("=" * 50)
            lines.append("")
            
            # Verifica se os textos desta página já estão no formato bilíngue
            already_bilingual = any(t.startswith("[EN]:") or t.startswith("[BR]:") for t in trans_texts)
            
            if bilingual_enabled and not already_bilingual:
                # Página não visitada: reconstroi combinando original + traduzido
                orig_texts = self.studio_pages_original.get(page, [])
                import itertools
                def split_blocks(lst):
                    return ["\n".join(g) for k, g in itertools.groupby(lst, key=bool) if k]
                t_blocks = split_blocks(trans_texts)
                o_blocks = split_blocks(orig_texts)
                for i, tblock in enumerate(t_blocks):
                    oblock = o_blocks[i] if i < len(o_blocks) else ""
                    if oblock:
                        lines.append(f"[EN]: {oblock}")
                        lines.append(f"[BR]: {tblock}")
                    else:
                        lines.append(tblock)
                    lines.append("")
            else:
                # Página já visitada (já no formato certo) ou modo não-bilíngue
                for t in trans_texts:
                    lines.append(t)
                    
            lines.append("")
            
        content = "\n".join(lines)
        
        # Caminho 1: Biblioteca Central
        biblioteca_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca"
        biblioteca_dir.mkdir(parents=True, exist_ok=True)
        caminho_1 = str(biblioteca_dir / nome_final)
        
        with open(caminho_1, "w", encoding="utf-8-sig") as f:
            f.write(content)
            
        msg = f"✅ Tradução finalizada!\nSalvo na Biblioteca: {caminho_1}"
            
        # Caminho 2: Pasta original das imagens ou Saída
        if hasattr(self, 'studio_images_paths') and self.studio_images_paths:
            out_path = self.entry_output.get().strip()
            if out_path:
                img_dir = out_path
            else:
                img_dir = os.path.dirname(list(self.studio_images_paths.values())[0])
                
            caminho_2 = os.path.join(img_dir, nome_final)
            try:
                import shutil
                shutil.copy2(caminho_1, caminho_2)
                msg += f"\nExportado para o Scanlator em: {caminho_2}"
            except Exception as e:
                msg += f"\n⚠️ Falha ao salvar cópia no Scanlator: {e}"
                
        self.log(msg)
        
        # Sincroniza a Memória RAG (V2)
        try:
            import sys
            install_dir = Path(__file__).parent if not getattr(sys, 'frozen', False) else Path(sys.executable).parent
            if str(install_dir) not in sys.path:
                sys.path.append(str(install_dir))
            import rag_memory
            
            workspace = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio"
            success, rag_msg = rag_memory.sync_memory_from_txts(workspace, [Path(caminho_1)])
            self.log(f"🧠 {rag_msg}")
        except Exception as e:
            self.log(f"⚠️ Erro ao atualizar Memória RAG: {e}")
            
        # Atualiza a view do Leitor
        self.reader_refresh_list()
        
        self.studio_translated_txt_path = caminho_1
        
        # Salva o dicionário local se estiver no modo editor
        if getattr(self, 'studio_is_editor_mode', False):
            local_content = self.textbox_studio_dict.get("0.0", "end-1c").strip()
            self.entry_dict_local.delete("0.0", "end")
            self.entry_dict_local.insert("end", local_content)
            try:
                with open(LOCAL_DICT_PATH, "w", encoding="utf-8") as f:
                    f.write(local_content)
            except: pass

    def save_and_continue(self):
        self.save_studio_text()
        
        if self.studio_translated_txt_path:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, str(self.studio_translated_txt_path))
        
        self.tabview.set("Processamento")
        self.var_ocr.set(False)
        self.var_pause_ocr.set(False)
        
        if self.var_correct.get() or self.var_translate.get():
            self.start_processing()
        else:
            self.log("\nNenhuma etapa seguinte estava selecionada para continuar.")



    def _get_drag_context(self, block):
        """Descobre em qual painel o bloco está para arrasto."""
        if hasattr(self, 'studio_blocks') and block in self.studio_blocks:
            return self.studio_blocks, self.frame_studio_blocks
        
        # Caso o bloco já tenha sido substituído pelo placeholder
        if hasattr(self, 'drag_placeholder'):
            if hasattr(self, 'studio_blocks') and self.drag_placeholder in self.studio_blocks:
                return self.studio_blocks, self.frame_studio_blocks
        return None, None

    def start_block_drag(self, block, event):
        target_list, target_frame = self._get_drag_context(block)
        if not target_list: return
        
        self.block_drag_start_y = event.y_root
        
        # Save relative grab position for smooth floating
        self.drag_offset_x = event.x_root - block.winfo_rootx()
        self.drag_offset_y = event.y_root - block.winfo_rooty()
        
        # Save dimensions BEFORE pack_forget so it doesn't change size
        h = block.winfo_height()
        
        # Create a placeholder frame to show where it will drop
        self.drag_placeholder = ctk.CTkFrame(target_frame, height=h, 
                                             fg_color="transparent", border_width=2, border_color="#555", corner_radius=5)
        
        # Replace block with placeholder in the list
        idx = target_list.index(block)
        target_list[idx] = self.drag_placeholder
        
        # Unpack the block and make it float using place()
        block.pack_forget()
        block.configure(width=target_frame.winfo_width())
        
        # Visually pack the placeholder so space is reserved
        self.repack_studio_blocks()

    def do_block_drag(self, block, event):
        target_list, target_frame = self._get_drag_context(block)
        if not target_frame: return
        
        # Move the floating block visually
        parent_x = target_frame.winfo_rootx()
        parent_y = target_frame.winfo_rooty()
        
        new_x = event.x_root - parent_x - self.drag_offset_x
        new_y = event.y_root - parent_y - self.drag_offset_y
        block.place(x=new_x, y=new_y)
        block.lift() # Ensure it stays on top of other packed blocks
        
        # Determine if we should swap placeholder position
        current_y = event.y_root
        
        if not hasattr(self, 'drag_placeholder') or self.drag_placeholder not in target_list:
            return
            
        idx = target_list.index(self.drag_placeholder)
        
        # Check if crossed the center of the block above
        if idx > 0:
            above_block = target_list[idx - 1]
            above_y = above_block.winfo_rooty()
            above_h = above_block.winfo_height()
            if current_y < above_y + (above_h / 2):
                target_list[idx], target_list[idx-1] = target_list[idx-1], target_list[idx]
                self.repack_studio_blocks()
                return
                
        # Check if crossed the center of the block below
        if idx < len(target_list) - 1:
            below_block = target_list[idx + 1]
            below_y = below_block.winfo_rooty()
            below_h = below_block.winfo_height()
            if current_y > below_y + (below_h / 2):
                target_list[idx], target_list[idx+1] = target_list[idx+1], target_list[idx]
                self.repack_studio_blocks()
                return
                
    def stop_block_drag(self, block, event):
        target_list, target_frame = self._get_drag_context(block)
        if not target_list: return
        
        if not hasattr(self, 'drag_placeholder'):
            return
            
        block.place_forget()
        
        if self.drag_placeholder in target_list:
            idx = target_list.index(self.drag_placeholder)
            target_list[idx] = block
            self.drag_placeholder.destroy()
        else:
            target_list.append(block)
            
        delattr(self, 'drag_placeholder')
        self.repack_studio_blocks()



    def delete_block(self, block):
        if hasattr(self, 'studio_blocks') and block in self.studio_blocks:
            self.studio_blocks.remove(block)
        block.destroy()



    def browse_path(self):
        path = filedialog.askdirectory(title="Selecione a pasta do capítulo (Recomendado)")
        if not path:
            path = filedialog.askopenfilename(title="Ou selecione uma imagem/arquivo", filetypes=[("Imagens e Textos", "*.png *.jpg *.jpeg *.webp *.txt")])
        if path:
            path = os.path.normpath(path)
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, path)

    def browse_output_path(self):
        path = filedialog.askdirectory(title="Selecione a Pasta de Saída (Opcional)")
        if path:
            path = os.path.normpath(path)
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, path)

    def log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def run_subprocess(self, command):
        import re
        import os
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.current_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", creationflags=creationflags, env=env)
        
        for line in iter(self.current_process.stdout.readline, ''):
            self.log(line.strip('\n'))
            match = re.search(r'\[(\d+)/(\d+)\]', line)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                if total > 0:
                    self.progress_bar.set(current / total)
            
        self.current_process.stdout.close()
        return_code = self.current_process.wait()
        self.current_process = None
        return return_code

    def _update_pipeline_status(self, folder_path, raw=None, corrigido=None, traduzido=None, nome_final=None):
        """Atualiza o status.json na Temp com o estado de processamento de cada pasta."""
        import json
        temp_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca" / "Temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        status_file = temp_dir / "status.json"
        
        p = Path(folder_path)
        if p.is_file() and p.suffix.lower() != ".txt":
            base_name = p.parent.name
        else:
            base_name = p.name if p.is_dir() else p.stem.replace("_raw", "").replace("_corrigido", "").replace("_traduzido", "")
        folder_key = base_name
        
        # Carrega o json existente ou cria novo
        all_status = {}
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    all_status = json.load(f)
            except Exception:
                all_status = {}
        
        if folder_key not in all_status:
            all_status[folder_key] = {}
        
        if raw:
            all_status[folder_key]["raw"] = raw
        if corrigido:
            all_status[folder_key]["corrigido"] = corrigido
        if traduzido:
            all_status[folder_key]["traduzido"] = traduzido
        if nome_final:
            all_status[folder_key]["nome_final"] = nome_final
        
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(all_status, f, ensure_ascii=False, indent=2)
        
        # Atualiza o semáforo na thread principal
        self.after(0, self.refresh_workspace)

    def cancel_processing(self):
        if hasattr(self, 'current_process') and self.current_process is not None:
            self.log("\n⚠️ CANCELAMENTO SOLICITADO. Abortando processo atual...")
            self.btn_cancel.configure(state="disabled", text="Abortando...")
            self.current_process.terminate()
            
            # Força o Ollama a descarregar o modelo da memória (VRAM)
            import threading
            def kill_ollama():
                try:
                    import urllib.request
                    import json
                    req = urllib.request.Request(
                        "http://127.0.0.1:11434/api/generate",
                        data=json.dumps({"model": "llama3.1:8b", "keep_alive": 0}).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(req, timeout=2)
                except:
                    pass
            threading.Thread(target=kill_ollama, daemon=True).start()

    def reset_processing_tab(self):
        """Limpa a aba de Processamento de volta ao estado inicial."""
        # Limpa o caminho
        self.entry_path.delete(0, "end")
        self.entry_output.delete(0, "end")
        # Limpa o log
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("0.0", "end")
        self.textbox_log.configure(state="disabled")
        # Reseta progresso
        self.progress_bar.set(0)
        self.lbl_current_step.configure(text="")
        # Reseta botões
        self.btn_run.configure(state="normal", text="▶ INICIAR PROCESSAMENTO")
        self.btn_cancel.configure(state="disabled", text="⏹ CANCELAR")
        # Limpa dicionário temporário
        self.entry_dict_local.delete("0.0", "end")
        # Reseta checkboxes para padrão
        self.var_ocr.set(True)
        self.var_correct.set(True)
        self.var_translate.set(True)
        self.var_pause_ocr.set(False)
        self.var_bilingual.set(False)


    def reset_studio_tab(self):
        """Limpa o Estúdio de Tradução de volta ao estado inicial."""
        # Limpa todos os blocos de texto
        for block in self.studio_blocks:
            block.destroy()
        self.studio_blocks = []
        # Limpa a barra lateral de páginas
        for widget in self.frame_studio_pages.winfo_children():
            widget.destroy()
        # Limpa a imagem do canvas
        self.canvas_studio_img.delete("all")
        self.studio_original_pil_image = None
        self.studio_img_id = None
        # Limpa o texto original
        self.textbox_studio_original.configure(state="normal")
        self.textbox_studio_original.delete("0.0", "end")
        self.textbox_studio_original.insert("0.0", "Selecione um bloco de tradução abaixo para ver o original...")
        self.textbox_studio_original.configure(state="disabled")
        # Reseta estado interno
        self.studio_pages_original = {}
        self.studio_pages_translated = {}
        self.studio_images_paths = {}
        self.studio_current_page = None
        self.studio_translated_txt_path = None

    def start_processing(self):
        path = self.entry_path.get()
        if not path or not os.path.exists(path):
            self.log("❌ ERRO: Caminho inválido ou não selecionado.")
            return


        run_ocr = self.var_ocr.get()
        run_correct = self.var_correct.get()
        run_translate = self.var_translate.get()
        
        # Validação Modular
        if run_ocr and not self.check_module_ocr():
            self.log("⚠️ ATENÇÃO: O Motor OCR não está instalado.")
            self.log("Vá até a aba 'Central de Módulos' e instale-o antes de usar a Etapa 1.")
            self.tabview.set("Central de Módulos")
            return
            
        if (run_correct or run_translate) and not self.check_module_translation():
            self.log("⚠️ ATENÇÃO: O Motor de Tradução (IA) não está instalado.")
            self.log("Vá até a aba 'Central de Módulos' e instale-o antes de usar as Etapas 2 e 3.")
            self.tabview.set("Central de Módulos")
            return

        
        # Salva o dicionário global no arquivo sempre que rodar
        dict_global_content = self.entry_dict_global.get("0.0", "end-1c").strip()
        with open(GLOBAL_DICT_PATH, "w", encoding="utf-8") as f:
            f.write(dict_global_content)
            
        dict_local_content = self.entry_dict_local.get("0.0", "end-1c").strip()
        out_path = self.entry_output.get().strip()

        if not (run_ocr or run_correct or run_translate):
            self.log("⚠️ Selecione pelo menos uma etapa de processamento nas caixas de seleção.")
            return

        self.btn_run.configure(state="disabled", text="⏳ PROCESSANDO (Aguarde)...")
        self.btn_cancel.configure(state="normal", text="⏹ CANCELAR")
        self.progress_bar.set(0)
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("0.0", "end")
        self.textbox_log.configure(state="disabled")
        
        bilingual = self.var_bilingual.get()
        pause_ocr = self.var_pause_ocr.get()
        tone = self.combo_tone.get()
        model_corr = self.combo_model_corr.get()
        model_trans = self.combo_model_trans.get()
        rag_workspace = str(self.workspace_dir) if getattr(self, "workspace_dir", None) and self.var_use_rag.get() else ""

        threading.Thread(target=self.process_pipeline, args=(path, out_path, run_ocr, run_correct, run_translate, dict_global_content, dict_local_content, bilingual, pause_ocr, tone, rag_workspace, model_corr, model_trans), daemon=True).start()

    def process_pipeline(self, input_path, out_path, run_ocr, run_correct, run_translate, dict_global, dict_local, bilingual, pause_ocr, tone, rag_workspace, model_corr="llama3.1:8b", model_trans="llama3.1:8b"):
        import time
        start_time = time.time()
        try:
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
                
            python_exe_ocr = str(install_dir / "venv_ocr" / "Scripts" / "python.exe")
            # If the user runs from source without venv_ui, fallback to sys.executable
            python_exe_ui = str(install_dir / "venv_ui" / "Scripts" / "python.exe")
            if not Path(python_exe_ui).exists():
                python_exe_ui = sys.executable
                
            current_target = input_path

            # Grava o dicionário local em um arquivo temporário no AppData
            with open(LOCAL_DICT_PATH, "w", encoding="utf-8") as f:
                f.write(dict_local)

            self.log("==================================================")
            self.log(f"🚀 INICIANDO PIPELINE: {os.path.basename(input_path)}")
            self.log("==================================================")
            
            p_input = Path(input_path)
            # Para imagens avulsas, usa o nome da pasta-mãe como identidade do capítulo na Temp
            if p_input.is_file() and p_input.suffix.lower() != ".txt":
                base_name = p_input.parent.name
            else:
                base_name = p_input.name if p_input.is_dir() else p_input.stem.replace("_raw", "").replace("_corrigido", "").replace("_traduzido", "")

            # Configura a Biblioteca e a pasta Temp
            biblioteca_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca"
            temp_dir = biblioteca_dir / "Temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            dir_ocr = str(temp_dir)
            dir_corr = str(temp_dir)
            dir_trans = str(temp_dir)

            if run_ocr:
                self.after(0, lambda: self.lbl_current_step.configure(text="[Etapa 1/3] Extraindo Texto (OCR)..."))
                self.log("\n>>> ETAPA 1: EXTRAÇÃO DE TEXTO BRUTO (GPU)")
                p = Path(input_path)
                if p.suffix.lower() == ".txt":
                    self.log("⚠️ Você selecionou um arquivo .txt mas deixou o Extrator de Imagem marcado.")
                    self.log("Pulando a Etapa 1 e usando o arquivo .txt fornecido...")
                else:
                    expected_txt_path = Path(dir_ocr) / f"{base_name}_raw.txt"
                    cmd = [python_exe_ocr, "manga_ocr.py", input_path, "--output", str(expected_txt_path)]
                    
                    if p.is_file():
                        # Auto-merge: procura APENAS o _raw.txt na Temp para a pasta-mãe desta imagem
                        target_txt = self._find_txt_in_temp(p.parent, ["_raw.txt"])
                        if target_txt:
                            expected_txt_path = target_txt
                            cmd = [python_exe_ocr, "manga_ocr.py", input_path, "--output", str(target_txt), "--append"]
                            self.log(f"🔗 Auto-Mesclagem ativada! Anexando página avulsa ao arquivo da Temp: {target_txt.name}")
                    
                    self.progress_bar.set(0)
                    if hasattr(self, 'var_use_gpu') and self.var_use_gpu.get():
                        cmd.append("--gpu")
                    
                    code = self.run_subprocess(cmd)
                    if code != 0:
                        self.log("❌ Falha ou Cancelamento na etapa de OCR. Abortando.")
                        return
                    current_target = str(expected_txt_path)
                    self._update_pipeline_status(input_path, raw=current_target)
                    
                    if pause_ocr:
                        self.log("\n⚠️ PAUSA MANUAL ATIVADA. Alternando para o Editor Visual...")
                        self.after(300, lambda fp=input_path, tp=current_target: self.load_editor_from_pipeline(fp, tp))
                        self.log("✅ Revise o texto no Editor Visual e adicione termos ao Dicionário Temporário.")
                        self.log("✅ Quando terminar, volte aqui, desmarque a Etapa 1, marque as Etapas 2 e 3 e clique em Iniciar.")
                        self.btn_run.configure(state="normal", text="▶ CONTINUAR PROCESSAMENTO")
                        self.btn_cancel.configure(state="disabled", text="⏹ CANCELAR")
                        self.progress_bar.set(0)
                        return

            if run_correct:
                self.after(0, lambda: self.lbl_current_step.configure(text="[Etapa 2/3] Corrigindo Textos (IA)..."))
                self.log(f"\n>>> ETAPA 2: POLIMENTO DE INGLÊS 99.9% (IA {model_corr})")
                if not current_target.endswith(".txt"):
                    self.log("❌ O arquivo base para a Correção precisa ser um .txt.")
                    return
                
                cmd = [python_exe_ui, "ocr_corrector.py", current_target, "--dict-global", str(GLOBAL_DICT_PATH), "--dict-local", str(LOCAL_DICT_PATH), "--output", dir_corr, "--model", model_corr]
                self.progress_bar.set(0)
                code = self.run_subprocess(cmd)
                if code != 0:
                        self.log("❌ Falha ou Cancelamento na etapa de Correção. Abortando.")
                        return
                
                # Atualiza target pro tradutor
                corr_input_stem = Path(current_target).stem.replace("_raw", "")
                current_target = str(Path(dir_corr) / f"{corr_input_stem}_corrigido.txt")
                self._update_pipeline_status(input_path, corrigido=current_target)

            if run_translate:
                self.after(0, lambda: self.lbl_current_step.configure(text="[Etapa 3/3] Traduzindo PT-BR (IA)..."))
                self.log(f"\n>>> ETAPA 3: TRADUÇÃO PT-BR (IA {model_trans})")
                if not current_target.endswith(".txt"):
                    self.log("❌ O arquivo base para Tradução precisa ser um .txt.")
                    return
                
                cmd = [python_exe_ui, "manga_translator.py", current_target, "--dict-global", str(GLOBAL_DICT_PATH), "--dict-local", str(LOCAL_DICT_PATH), "--output", dir_trans, "--model", model_trans]
                if bilingual:
                    cmd.append("--bilingual")
                if tone:
                    cmd.extend(["--tone", tone])
                if rag_workspace:
                    cmd.extend(["--rag-workspace", rag_workspace])
                
                self.progress_bar.set(0)
                code = self.run_subprocess(cmd)
                if code != 0:
                    self.log("❌ Falha ou Cancelamento na etapa de Tradução. Abortando.")
                    return
                
                # O nome do arquivo de saida é derivado do stem do arquivo de entrada do tradutor
                # (que pode ser 009_corrigido.txt -> saida 009_traduzido.txt)
                trans_input_stem = Path(current_target).stem.replace("_corrigido", "").replace("_raw", "")
                current_target = str(Path(dir_trans) / f"{trans_input_stem}_traduzido.txt")
                self._update_pipeline_status(input_path, traduzido=current_target)
                
                pause_translate = self.var_pause_translate.get()
                if pause_translate:
                    self.log("\n⚠️ PAUSA MANUAL ATIVADA. Alternando para o Estúdio de Tradução...")
                    self.after(300, lambda fp=input_path, tp=current_target: self.load_studio_from_pipeline(fp, tp))
                    self.log("✅ Revise o texto no Estúdio de Tradução.")
                    self.btn_run.configure(state="normal", text="▶ INICIAR PROCESSAMENTO")
                    self.btn_cancel.configure(state="disabled", text="⏹ CANCELAR")
                    self.progress_bar.set(0)
                    return

            # --- START SUMMARY STATS ---
            end_time = time.time()
            total_seconds = end_time - start_time
            total_pages = 0
            total_balloons = 0
            
            if current_target and Path(current_target).exists():
                with open(current_target, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PÁGINA "):
                            total_pages += 1
                        elif line.strip() and not line.startswith("===") and "[IGNORE]" not in line and not line.startswith("[Nenhum texto"):
                            total_balloons += 1
            
            if total_pages == 0: total_pages = 1 # fallback se não achou PÁGINA
            avg_time_page = total_seconds / total_pages
            avg_time_balloon = total_seconds / total_balloons if total_balloons > 0 else 0
            
            self.log("\n==================================================")
            self.log("📊 RELATÓRIO DE PROCESSAMENTO")
            self.log(f"📄 Páginas Processadas: {total_pages}")
            self.log(f"💬 Falas/Balões Extraídos: {total_balloons}")
            self.log(f"⏱️ Tempo Total: {total_seconds:.1f} segundos")
            self.log(f"⚡ Média: {avg_time_page:.1f} seg / pág | {avg_time_balloon:.1f} seg / balão")
            self.log("==================================================")
            # --- END SUMMARY STATS ---

            self.after(0, lambda: self.lbl_current_step.configure(text="Finalizando..."))
            
            # Verifica se já existe um nome_final salvo para esta pasta no status.json
            import json
            status_file = temp_dir / "status.json"
            existing_nome = None
            p_input = Path(input_path)
            if p_input.is_file() and p_input.suffix.lower() != ".txt":
                folder_key_check = p_input.parent.name
            else:
                folder_key_check = p_input.name if p_input.is_dir() else p_input.stem.replace("_raw", "").replace("_corrigido", "").replace("_traduzido", "")
            
            if status_file.exists():
                try:
                    with open(status_file, "r", encoding="utf-8") as f:
                        all_st = json.load(f)
                    existing_nome = all_st.get(folder_key_check, {}).get("nome_final")
                except Exception:
                    pass
            
            if existing_nome:
                # Auto-atualização: já tem nome, atualiza Biblioteca Central e pasta de imagens
                import shutil
                nome_final = existing_nome if existing_nome.endswith(".txt") else existing_nome + ".txt"
                
                dest_biblioteca = biblioteca_dir / nome_final
                shutil.copy2(current_target, dest_biblioteca)
                self.log(f"\n🔄 Auto-atualização! Biblioteca Central atualizada: {dest_biblioteca}")
                
                scanlator_dir = out_path if out_path else (str(p_input.parent) if p_input.is_file() else str(p_input))
                dest_scanlator = Path(scanlator_dir) / nome_final
                shutil.copy2(current_target, dest_scanlator)
                self.log(f"🔄 Pasta do Scanlator atualizada: {dest_scanlator}")
                self.log(f"\n✨ PROCESSO CONCLUÍDO! Arquivo '{nome_final}' atualizado automaticamente em todos os destinos! ✨")
            else:
                # Primeira vez: pede o nome e salva no status.json
                self.log("\n✨ PROCESSO CONCLUÍDO! AGUARDANDO NOME FINAL... ✨")
                
                def ask_final_name():
                    dialog = ctk.CTkInputDialog(text="Processo 100% concluído!\nDigite o nome final do capítulo para salvar e exportar (sem .txt):", title="Finalizar Exportação")
                    nome_final = dialog.get_input()
                    if nome_final:
                        nome_final = nome_final.strip()
                        if not nome_final.endswith(".txt"):
                            nome_final += ".txt"
                        
                        import shutil
                        # Salva na biblioteca raiz
                        dest_biblioteca = biblioteca_dir / nome_final
                        shutil.copy2(current_target, dest_biblioteca)
                        self.log(f"\n✅ Salvo na Biblioteca: {dest_biblioteca}")
                        
                        # Salva na pasta do scanlator
                        scanlator_dir = out_path if out_path else (str(p_input.parent) if p_input.is_file() else str(p_input))
                        dest_scanlator = Path(scanlator_dir) / nome_final
                        shutil.copy2(current_target, dest_scanlator)
                        self.log(f"✅ Exportado para o Scanlator: {dest_scanlator}")
                        
                        # Salva o nome no status.json para auto-atualização futura
                        self._update_pipeline_status(input_path, nome_final=nome_final)
                        self.log(f"💾 Nome '{nome_final}' memorizado. Processamentos futuros desta pasta atualizarão automaticamente!")
                    else:
                        self.log("\n⚠️ Exportação cancelada. O arquivo ficou apenas na pasta Temp da Biblioteca.")

                self.after(100, ask_final_name)

        except Exception as e:
            self.log(f"\n❌ ERRO INESPERADO: {e}")
        finally:
            end_time = time.time()
            elapsed_time = end_time - start_time
            balloon_count = 0
            page_count = 0
            try:
                import re
                if current_target and os.path.exists(current_target) and current_target.endswith(".txt"):
                    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
                        try:
                            with open(current_target, "r", encoding=enc) as f:
                                content = f.read()
                            break
                        except Exception:
                            pass
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
                    pages = [l for l in lines if re.match(r'^P.{0,2}GINA', l, re.IGNORECASE) or l.startswith('===')]
                    page_count = len(pages)
                    balloons = [l for l in lines if not re.match(r'^P.{0,2}GINA', l, re.IGNORECASE) and not l.startswith('===')]
                    if any(l.startswith('[BR]') for l in balloons):
                        balloon_count = len([l for l in balloons if l.startswith('[BR]')])
                    else:
                        balloon_count = len(balloons)
            except Exception:
                pass
                
            self.log("\n==================================================")
            self.log(f"⏱️ TEMPO TOTAL DA PIPELINE: {elapsed_time:.1f} segundos")
            if balloon_count > 0:
                self.log(f"📊 {balloon_count} blocos de texto/balões em {page_count} páginas processadas.")
                self.log(f"⚡ Média: {elapsed_time/balloon_count:.1f} seg/balão | {elapsed_time/max(1, page_count):.1f} seg/página")
            self.log("==================================================\n")

            self.after(0, lambda: self.lbl_current_step.configure(text=""))
            self.btn_run.configure(state="normal", text="▶ INICIAR PROCESSAMENTO")
            self.btn_cancel.configure(state="disabled", text="⏹ CANCELAR")
            self.progress_bar.set(0)


    def _pkg_exists_anywhere(self, *pkg_names):
        """
        Verifica se os pacotes existem estritamente no venv_ocr isolado.
        """
        import subprocess
        import sys
        from pathlib import Path

        def can_import(py_exe):
            """Tenta importar todos os pacotes nesse Python."""
            try:
                import os
                env = os.environ.copy()
                env.pop("PYTHONPATH", None)
                env.pop("PYTHONHOME", None)
                code = "; ".join(f"import {p}" for p in pkg_names)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                r = subprocess.run(
                    [py_exe, "-c", code],
                    capture_output=True, timeout=15,
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                    startupinfo=startupinfo,
                    env=env
                )
                return r.returncode == 0
            except Exception:
                return False

        # Verifica no venv_ocr e no venv_ui
        if getattr(sys, 'frozen', False):
            install_dir = Path(sys.executable).parent
        else:
            install_dir = Path(__file__).parent

        venv_ocr_python = install_dir / "venv_ocr" / "Scripts" / "python.exe"
        if venv_ocr_python.exists() and can_import(str(venv_ocr_python)):
            return True
            
        venv_ui_python = install_dir / "venv_ui" / "Scripts" / "python.exe"
        if venv_ui_python.exists() and can_import(str(venv_ui_python)):
            return True

        return False

    
    def check_module_rag(self):
        return self._pkg_exists_anywhere("chromadb", "sentence_transformers")

    def install_rag(self):
        self.btn_install_rag.configure(state="disabled", text="Instalando...")
        self.log_rag.pack(fill="x", padx=15, pady=(0, 15))
        self.log_rag.configure(state="normal")
        self.log_rag.delete("0.0", "end")
        self.log_rag.configure(state="disabled")

        def worker():
            import subprocess
            import sys
            import venv
            import os
            
            self._ui_log(self.log_rag, "▶ Baixando e instalando ChromaDB e SentenceTransformers (pode demorar)...")
            
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
                
            venv_path = install_dir / "venv_ui"
            if not venv_path.exists():
                venv.EnvBuilder(with_pip=True).create(venv_path)
                
            pip_exe = str(venv_path / "Scripts" / "pip.exe")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            import os
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            
            proc = subprocess.Popen([pip_exe, "install", "chromadb", "sentence-transformers", "rapidfuzz"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000, startupinfo=startupinfo, env=env)
            for line in proc.stdout:
                if line.strip():
                    self._ui_log(self.log_rag, line.strip())
                    self.after(0, lambda: self._bump_progress(self.pb_rag))
            proc.wait()
            
            if proc.returncode == 0:
                self._ui_log(self.log_rag, "✅ Motor RAG instalado com sucesso!")
            else:
                self._ui_log(self.log_rag, "❌ Falha ao instalar dependências.")
            
            self.after(500, self.refresh_module_status)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def check_module_ocr(self):
        try:
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
            venv_ocr_python = install_dir / "venv_ocr" / "Scripts" / "python.exe"
            if not venv_ocr_python.exists(): 
                return False
            import os
            import subprocess
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            creationflags = 0x08000000 if sys.platform == "win32" else 0
            res = subprocess.run([str(venv_ocr_python), "-c", "import transformers; print(transformers.__version__)"], capture_output=True, text=True, creationflags=creationflags, env=env)
            if res.returncode == 0:
                ver = res.stdout.strip()
                if ver != "4.38.2":
                    return False
        except:
            pass
        return self._pkg_exists_anywhere("transformers", "einops")

    def check_module_translation(self):
        import shutil
        import subprocess
        
        # O módulo de tradução e RAG compartilham a mesma venv (venv_ui)
        if getattr(sys, 'frozen', False):
            install_dir = Path(sys.executable).parent
        else:
            install_dir = Path(__file__).parent
        venv_path = install_dir / "venv_ui"
        if not venv_path.exists():
            return False
            
        if not shutil.which("ollama"):
            import os
            default_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
            if default_path.exists():
                os.environ["PATH"] += os.pathsep + str(default_path.parent)
            else:
                return False
        try:
            import urllib.request
            import json
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                return any("llama3.1:8b" in m for m in models)
        except Exception:
            return False


    def check_for_updates(self):
        import urllib.request
        import json
        from tkinter import messagebox
        import sys
        import subprocess
        
        url_version = "https://raw.githubusercontent.com/CHARLINKK/manga-ai-studio/main/version.json"
        
        try:
            req = urllib.request.Request(url_version, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                remote_data = json.loads(response.read().decode())
                
            remote_version = remote_data.get("version", "1.0.0")
            download_url = remote_data.get("download_url", "")
            
            # Lê versão local
            local_version = "v1.3.11"
            version_file = Path("version.json")
            if version_file.exists():
                with open(version_file, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    local_version = local_data.get("version", "1.0.0")
                    
            if remote_version != local_version and download_url:
                msg = f"Nova versão encontrada: {remote_version}\nNovidades: {remote_data.get('changelog', '')}\n\nDeseja baixar e instalar agora? (O programa será reiniciado automaticamente)"
                if messagebox.askyesno("Atualização Disponível", msg):
                    self.perform_auto_update(download_url)
            elif remote_version != local_version:
                msg = f"Nova versão encontrada: {remote_version}, mas sem link de download direto.\nDeseja abrir a página de download agora?"
                if messagebox.askyesno("Atualização Disponível", msg):
                    import webbrowser
                    webbrowser.open("https://github.com/CHARLINKK/manga-ai-studio/releases/latest")
            else:
                messagebox.showinfo("Atualizado", "Você já está usando a versão mais recente!")
                
        except Exception as e:
            messagebox.showerror("Erro de Atualização", f"Não foi possível checar por atualizações.\nDetalhes: {e}")

    def perform_auto_update(self, download_url):
        import urllib.request
        import zipfile
        import tempfile
        import threading
        import subprocess
        import sys
        
        top = ctk.CTkToplevel(self)
        top.title("Atualizando Manga AI Studio")
        top.geometry("400x150")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.grab_set()
        
        lbl_status = ctk.CTkLabel(top, text="Iniciando download...", font=ctk.CTkFont(weight="bold"))
        lbl_status.pack(pady=(20, 10))
        
        pb = ctk.CTkProgressBar(top, width=300)
        pb.pack(pady=10)
        pb.set(0)
        
        def worker():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "MangaAIStudio_Update"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                is_zip = download_url.lower().endswith(".zip")
                dest_file = temp_dir / ("update.zip" if is_zip else "update.exe")
                
                def reporthook(blocknum, blocksize, totalsize):
                    if totalsize > 0:
                        read = blocknum * blocksize
                        p = min(read / totalsize, 1.0)
                        self.after(0, lambda: pb.set(p * 0.8))
                        self.after(0, lambda: lbl_status.configure(text=f"Baixando: {int(p*100)}%"))
                        
                urllib.request.urlretrieve(download_url, str(dest_file), reporthook)
                
                exe_path = dest_file
                
                if is_zip:
                    self.after(0, lambda: lbl_status.configure(text="Extraindo arquivos..."))
                    with zipfile.ZipFile(dest_file, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    try: dest_file.unlink() # Exclui o .zip para economizar espaço
                    except: pass
                    
                    self.after(0, lambda: pb.set(0.95))
                    
                    exes = list(temp_dir.glob("*.exe"))
                    if not exes:
                        raise Exception("Nenhum arquivo .exe encontrado no ZIP.")
                    exe_path = exes[0]
                
                self.after(0, lambda: lbl_status.configure(text="Instalando..."))
                self.after(0, lambda: pb.set(1.0))
                
                subprocess.Popen([str(exe_path), "--silent"], creationflags=subprocess.CREATE_NO_WINDOW)
                self.after(500, sys.exit)
                
            except Exception as e:
                self.after(0, lambda: lbl_status.configure(text="Erro ao atualizar!"))
                from tkinter import messagebox
                self.after(0, lambda: messagebox.showerror("Erro de Atualização", f"Falha ao baixar/instalar: {e}"))
                self.after(0, top.destroy)

        threading.Thread(target=worker, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    #  ABA LEITOR (BLOCO DE NOTAS)
    # ═══════════════════════════════════════════════════════════════════════════

    def setup_reader_tab(self):
        self.tab_reader.columnconfigure(1, weight=1)
        self.tab_reader.rowconfigure(0, weight=1)
        
        # Painel Esquerdo (Lista de Arquivos da Biblioteca)
        self.frame_reader_sidebar = ctk.CTkFrame(self.tab_reader, width=250)
        self.frame_reader_sidebar.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        self.frame_reader_sidebar.pack_propagate(False)
        
        lbl_sidebar = ctk.CTkLabel(self.frame_reader_sidebar, text="Sua Biblioteca", font=ctk.CTkFont(weight="bold", size=16))
        lbl_sidebar.pack(pady=10)
        
        btn_refresh = ctk.CTkButton(self.frame_reader_sidebar, text="🔄 Atualizar Lista", command=self.reader_refresh_list)
        btn_refresh.pack(padx=10, pady=(0, 10))
        
        self.reader_list_frame = ctk.CTkScrollableFrame(self.frame_reader_sidebar)
        self.reader_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Painel Direito (Leitor / Editor)
        self.frame_reader_main = ctk.CTkFrame(self.tab_reader)
        self.frame_reader_main.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.frame_reader_main.rowconfigure(1, weight=1)
        self.frame_reader_main.columnconfigure(0, weight=1)
        
        # Barra superior do leitor
        top_bar = ctk.CTkFrame(self.frame_reader_main, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.lbl_reader_file = ctk.CTkLabel(top_bar, text="Nenhum arquivo selecionado", text_color="#888", font=ctk.CTkFont(weight="bold"))
        self.lbl_reader_file.pack(side="left", padx=5, pady=5)
        
        self.btn_reader_save = ctk.CTkButton(top_bar, text="💾 Salvar Alterações", fg_color="#27ae60", hover_color="#2ecc71", command=self.reader_save_file, width=150, state="disabled")
        self.btn_reader_save.pack(side="right", padx=5, pady=5)
        
        self.reader_edit_var = ctk.BooleanVar(value=False)
        chk_edit = ctk.CTkCheckBox(top_bar, text="Habilitar Edição", variable=self.reader_edit_var, command=self.reader_toggle_edit)
        chk_edit.pack(side="right", padx=20, pady=5)
        
        # Área de texto principal
        self.reader_textbox = ctk.CTkTextbox(self.frame_reader_main, font=ctk.CTkFont(family="Consolas", size=14), wrap="word")
        self.reader_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.reader_textbox.configure(state="disabled")
        
        self.reader_current_file = None
        
        # Carrega a lista inicial
        self.reader_refresh_list()
        
    def reader_refresh_list(self):
        # Limpa lista atual
        for widget in self.reader_list_frame.winfo_children():
            widget.destroy()
            
        biblioteca_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Manga AI Studio" / "Biblioteca"
        if not biblioteca_dir.exists():
            lbl_empty = ctk.CTkLabel(self.reader_list_frame, text="Biblioteca vazia.", text_color="#888")
            lbl_empty.pack(pady=20)
            return
            
        # Lista arquivos .txt na raiz (Biblioteca Central)
        txt_files = [f for f in biblioteca_dir.iterdir() if f.is_file() and f.suffix.lower() == ".txt"]
        
        if not txt_files:
            lbl_empty = ctk.CTkLabel(self.reader_list_frame, text="Nenhum arquivo finalizado.", text_color="#888")
            lbl_empty.pack(pady=20)
            return
            
        # Ordena por data de modificação (mais recente primeiro)
        txt_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for fpath in txt_files:
            btn = ctk.CTkButton(self.reader_list_frame, text="📖 " + fpath.name, anchor="w", fg_color="transparent", hover_color="#444", text_color="#ddd", command=lambda p=fpath: self.reader_load_from_sidebar(p))
            btn.pack(fill="x", pady=2)

    def reader_load_from_sidebar(self, file_path):
        if not file_path.exists(): return
        
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
                
        self.reader_current_file = str(file_path)
        self.lbl_reader_file.configure(text=file_path.name)
        
        self.reader_textbox.configure(state="normal")
        self.reader_textbox.delete("0.0", "end")
        
        # Configura tags de estilo no widget interno tk.Text
        inner = self.reader_textbox._textbox
        inner.tag_configure("en_line",     foreground="#777777", font=("Consolas", 10, "italic"))
        inner.tag_configure("en_label",    foreground="#555555", font=("Consolas", 10, "italic"))
        inner.tag_configure("br_line",     foreground="#e8e8e8", font=("Consolas", 12, "normal"))
        inner.tag_configure("br_label",    foreground="#4a9eff", font=("Consolas", 12, "bold"))
        inner.tag_configure("separator",   foreground="#444444", font=("Consolas", 9, "normal"))
        inner.tag_configure("page_header", foreground="#f0c040", font=("Consolas", 11, "bold"))
        inner.tag_configure("normal",      foreground="#cccccc", font=("Consolas", 11, "normal"))
        
        is_bilingual = "[EN]:" in content.upper() or "[BR]:" in content.upper()
        
        if is_bilingual:
            # Renderização bilíngue com estilos diferenciados
            for line in content.split("\n"):
                ls = line.rstrip("\r")
                if ls.startswith("==="):
                    self.reader_textbox.insert("end", ls + "\n")
                    # aplica tag no que acabou de inserir
                    start = inner.index("end-1l")
                    end   = inner.index("end-1c")
                    inner.tag_add("separator", start, end)
                elif ls.upper().startswith("P") and ("GINA" in ls.upper()) and ":" in ls:
                    self.reader_textbox.insert("end", ls + "\n")
                    start = inner.index("end-1l")
                    end   = inner.index("end-1c")
                    inner.tag_add("page_header", start, end)
                elif ls.upper().startswith("[EN]:"):
                    label = ls[:6] + " " if ls.startswith("[") else "[EN]: "
                    text  = ls[5:]
                    self.reader_textbox.insert("end", label)
                    s1 = inner.index("end-1c linestart")
                    e1 = f"end-{len(text)+1}c"
                    inner.tag_add("en_label", s1, f"{s1}+{len(label)}c")
                    self.reader_textbox.insert("end", text + "\n")
                    start = inner.index("end-1l")
                    end   = inner.index("end-1c")
                    inner.tag_add("en_line", f"{start}+{len(label)}c", end)
                elif ls.upper().startswith("[BR]:"):
                    label = ls[:6] + " " if ls.startswith("[") else "[BR]: "
                    text  = ls[5:]
                    self.reader_textbox.insert("end", label)
                    s1 = inner.index("end-1c linestart")
                    inner.tag_add("br_label", s1, f"{s1}+{len(label)}c")
                    self.reader_textbox.insert("end", text + "\n")
                    start = inner.index("end-1l")
                    end   = inner.index("end-1c")
                    inner.tag_add("br_line", f"{start}+{len(label)}c", end)
                else:
                    self.reader_textbox.insert("end", ls + "\n")
        else:
            # Arquivo não-bilíngue: renderiza normal
            self.reader_textbox.insert("0.0", content)
        
        if not self.reader_edit_var.get():
            self.reader_textbox.configure(state="disabled")

    def reader_toggle_edit(self):
        if self.reader_edit_var.get():
            self.reader_textbox.configure(state="normal")
            self.btn_reader_save.configure(state="normal")
        else:
            self.reader_textbox.configure(state="disabled")
            self.btn_reader_save.configure(state="disabled")

    def reader_save_file(self):
        if not self.reader_current_file: return
        content = self.reader_textbox.get("0.0", "end-1c")
        try:
            with open(self.reader_current_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Pequeno feedback visual no botão
            old_text = self.btn_reader_save.cget("text")
            self.btn_reader_save.configure(text="✅ Salvo!")
            self.after(2000, lambda: self.btn_reader_save.configure(text=old_text))
        except Exception as e:
            self.log(f"Erro ao salvar arquivo no Leitor: {e}")
    def calculate_models_size(self):
        import os
        from pathlib import Path
        total_bytes = 0
        
        # HuggingFace Cache
        hf_cache = Path(os.environ.get("USERPROFILE", "")) / ".cache" / "huggingface" / "hub"
        if hf_cache.exists():
            try:
                for f in hf_cache.rglob('*'):
                    if f.is_file():
                        total_bytes += f.stat().st_size
            except Exception: pass
                    
        # Ollama Models
        ollama_models = Path(os.environ.get("USERPROFILE", "")) / ".ollama" / "models"
        if ollama_models.exists():
            try:
                for f in ollama_models.rglob('*'):
                    if f.is_file():
                        total_bytes += f.stat().st_size
            except Exception: pass
                    
        gb = total_bytes / (1024**3)
        return f"{gb:.2f} GB"

    def clear_hf_cache(self):
        import os
        import shutil
        from pathlib import Path
        import tkinter.messagebox as mb
        if not mb.askyesno("Apagar Modelos Base (OCR/RAG)", "Tem certeza que deseja apagar os modelos do HuggingFace armazenados em cache?\nIsso liberará espaço, mas os modelos precisarão ser baixados de novo automaticamente quando você for extrair textos ou usar a Memória de Contexto."): return
        hf_cache = Path(os.environ.get("USERPROFILE", "")) / ".cache" / "huggingface" / "hub"
        if hf_cache.exists():
            try:
                shutil.rmtree(hf_cache)
                mb.showinfo("Sucesso", "Cache do HuggingFace apagado com sucesso.")
            except Exception as e:
                mb.showerror("Erro", f"Falha ao apagar cache: {e}")
        self.refresh_module_status()

    def delete_ollama_model(self):
        import subprocess
        import tkinter.messagebox as mb
        model = self.combo_model_corr.get()
        if not mb.askyesno("Confirmar Exclusão", f"Tem certeza que deseja apagar o modelo '{model}' do Ollama?"): return
        try:
            subprocess.run(["ollama", "rm", model], creationflags=subprocess.CREATE_NO_WINDOW)
            mb.showinfo("Sucesso", f"Modelo '{model}' apagado com sucesso.")
        except Exception as e:
            mb.showerror("Erro", f"Falha ao apagar modelo: {e}")
        self.refresh_module_status()

    def pull_ollama_model(self):
        model = self.combo_model_corr.get()
        if not model: return
        self.btn_pull_ollama.configure(state="disabled", text="Puxando...")
        self.log_trans.pack(fill="x", padx=15, pady=(0, 15))
        self.log_trans.configure(state="normal")
        self.log_trans.delete("0.0", "end")
        self.log_trans.configure(state="disabled")

        def worker():
            import subprocess
            import re
            try:
                startupinfo_pull = subprocess.STARTUPINFO()
                startupinfo_pull.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                proc = subprocess.Popen(["ollama", "pull", model], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000, startupinfo=startupinfo_pull)
                
                for line in proc.stdout:
                    if not line.strip(): continue
                    # Atualiza log
                    self._ui_log(self.log_trans, line.strip())
                    
                    # Tenta capturar %
                    m = re.search(r'(\d+)%', line)
                    if m:
                        pct = int(m.group(1)) / 100.0
                        self.after(0, lambda v=pct: self.pb_trans.set(v))
                    else:
                        self.after(0, lambda: self._bump_progress(self.pb_trans))
                
                proc.wait()
                if proc.returncode == 0:
                    self._ui_log(self.log_trans, f"✅ Modelo {model} baixado com sucesso!")
                else:
                    self._ui_log(self.log_trans, f"❌ Erro ao puxar o modelo {model}.")
            except Exception as e:
                self._ui_log(self.log_trans, f"❌ Exceção: {e}")
            finally:
                self.after(0, self.refresh_module_status)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def uninstall_module(self, module_name):
        import shutil
        import os
        from pathlib import Path
        import tkinter.messagebox as mb
        import subprocess
        import sys
        
        if getattr(sys, 'frozen', False):
            install_dir = Path(sys.executable).parent
        else:
            install_dir = Path(__file__).parent
            
        if module_name == "ocr":
            if not mb.askyesno("Desinstalar OCR", "Tem certeza que deseja apagar o ambiente virtual do OCR e CUDA? Isso vai liberar bastante espaço, mas você precisará reinstalar para extrair textos."): return
            venv_path = install_dir / "venv_ocr"
            try:
                if venv_path.exists(): shutil.rmtree(venv_path)
                mb.showinfo("Sucesso", "Módulo OCR desinstalado.")
            except Exception as e:
                mb.showerror("Erro", f"Erro: {e}")
                
        elif module_name == "cuda":
            if not mb.askyesno("Desinstalar CUDA", "Tem certeza que deseja remover o suporte a GPU? O OCR ficará mais lento."): return
            pip_exe = install_dir / "venv_ocr" / "Scripts" / "pip.exe"
            if pip_exe.exists():
                try:
                    subprocess.run([str(pip_exe), "uninstall", "-y", "torch", "torchvision", "torchaudio", "triton", "bitsandbytes"], creationflags=0x08000000)
                    mb.showinfo("Sucesso", "Suporte CUDA removido.")
                except Exception as e:
                    mb.showerror("Erro", f"Erro: {e}")
                    
        elif module_name == "rag":
            if not mb.askyesno("Desinstalar Memória RAG", "Tem certeza que deseja remover a biblioteca do RAG? (O histórico em si será mantido)."): return
            pip_exe = install_dir / "venv_ui" / "Scripts" / "pip.exe"
            if pip_exe.exists():
                try:
                    subprocess.run([str(pip_exe), "uninstall", "-y", "chromadb", "sentence-transformers"], creationflags=0x08000000)
                    mb.showinfo("Sucesso", "Memória RAG removida.")
                except Exception as e:
                    mb.showerror("Erro", f"Erro: {e}")
                    
        self.refresh_module_status()

    def setup_modules_tab(self):

        self.frame_modules = ctk.CTkScrollableFrame(self.tab_modules, fg_color="transparent")
        self.frame_modules.pack(fill="both", expand=True, padx=20, pady=20)


        ctk.CTkLabel(self.frame_modules, text="Gerenciador de Módulos (IA)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 20))
        
        self.btn_update_app = ctk.CTkButton(self.frame_modules, text="🔄 Verificar Atualizações", fg_color="#3498db", hover_color="#2980b9", command=self.check_for_updates)
        self.btn_update_app.place(relx=0.98, rely=0.0, anchor="ne")

        # Lê a versão atual para exibir
        current_version_str = "v1.0.0"
        try:
            import sys, os, json
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            version_path = os.path.join(base_path, 'version.json')
            with open(version_path, "r", encoding="utf-8") as f:
                ver_data = json.load(f)
                current_version_str = f"v{ver_data.get('version', '1.0.0')}"
        except Exception:
            pass


    # Espaço extra no final para evitar corte na fonte itálica do tkinter
        self.lbl_app_version = ctk.CTkLabel(self.frame_modules, text=f"Versão: {current_version_str} ", font=ctk.CTkFont(size=12, slant="italic"), text_color="#777")
        self.lbl_app_version.place(relx=0.97, rely=0.06, anchor="ne")

        ctk.CTkLabel(self.frame_modules, text="Instale apenas o que você precisa. Módulos pesados são opcionais.", font=ctk.CTkFont(size=14), text_color="#ccc").pack(anchor="w", pady=(0, 20))

        # Card Armazenamento
        self.card_storage = ctk.CTkFrame(self.frame_modules, fg_color="#34495e", corner_radius=10)
        self.card_storage.pack(fill="x", pady=(0, 10), padx=10)
        
        self.lbl_storage = ctk.CTkLabel(self.card_storage, text="💾 Armazenamento Ocupado pelos Modelos de IA: Calculando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_storage.pack(side="left", padx=15, pady=15)
        
        self.btn_clear_hf = ctk.CTkButton(self.card_storage, text="🗑️ Apagar Modelos OCR/RAG (Cache)", fg_color="#c0392b", hover_color="#e74c3c", width=220, command=self.clear_hf_cache)
        self.btn_clear_hf.pack(side="right", padx=(5, 15), pady=15)


        # Card OCR
        self.card_ocr = ctk.CTkFrame(self.frame_modules, fg_color="#1a1a2e", corner_radius=10)
        self.card_ocr.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(self.card_ocr, text="📚 Motor de Extração de Texto (OCR Base)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.card_ocr, text="Necessário para a Etapa 1. Florence-2-Large (GPU/CPU). Tamanho: ~2.5 GB", font=ctk.CTkFont(size=12), text_color="#aaa").pack(anchor="w", padx=15, pady=(0, 10))
        
        self.lbl_status_ocr = ctk.CTkLabel(self.card_ocr, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_ocr.pack(side="left", padx=15, pady=15)
        self.pb_ocr = ctk.CTkProgressBar(self.card_ocr, mode="determinate", width=150)
        self.pb_ocr.pack(side="left", padx=10, pady=15)
        self.pb_ocr.set(0)
        
        self.btn_verify_ocr = ctk.CTkButton(self.card_ocr, text="🔄 Verificar", fg_color="#444", hover_color="#555", width=100, command=self.refresh_module_status)
        self.btn_verify_ocr.pack(side="right", padx=(5, 15), pady=15)
        
        self.btn_install_ocr = ctk.CTkButton(self.card_ocr, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_ocr)
        self.btn_install_ocr.pack(side="right", padx=(5, 5), pady=15)
        
        self.btn_uninstall_ocr = ctk.CTkButton(self.card_ocr, text="🗑️ Desinstalar", fg_color="#c0392b", hover_color="#e74c3c", width=100, command=lambda: self.uninstall_module("ocr"))
        self.btn_uninstall_ocr.pack(side="right", padx=(15, 5), pady=15)
        
        self.log_ocr = ctk.CTkTextbox(self.card_ocr, height=100, state="disabled", fg_color="#000")

        # Card CUDA
        self.card_cuda = ctk.CTkFrame(self.frame_modules, fg_color="#2c3e50", corner_radius=10)
        self.card_cuda.pack(fill="x", pady=(0, 10), padx=10)

        ctk.CTkLabel(self.card_cuda, text="⚡ Aceleração NVIDIA (CUDA)", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2ecc71").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.card_cuda, text="Exclusivo para placas NVIDIA. Acelera drasticamente a extração OCR. Tamanho: ~2.5 GB", font=ctk.CTkFont(size=12), text_color="#aaa").pack(anchor="w", padx=15, pady=(0, 10))

        self.lbl_status_cuda = ctk.CTkLabel(self.card_cuda, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_cuda.pack(side="left", padx=15, pady=15)
        self.pb_cuda = ctk.CTkProgressBar(self.card_cuda, mode="determinate", width=100)
        self.pb_cuda.pack(side="left", padx=10, pady=15)
        self.pb_cuda.set(0)

        self.var_use_gpu = ctk.BooleanVar(value=True)
        self.switch_gpu = ctk.CTkSwitch(self.card_cuda, text="Forçar Uso da GPU no OCR", variable=self.var_use_gpu, font=ctk.CTkFont(weight="bold"), fg_color="#444", progress_color="#2ecc71")
        self.switch_gpu.pack(side="left", padx=15, pady=15)

        self.btn_test_gpu = ctk.CTkButton(self.card_cuda, text="⚡ Testar Placa de Vídeo", fg_color="#8e44ad", hover_color="#9b59b6", width=160, command=self.verify_cuda_support)
        self.btn_test_gpu.pack(side="right", padx=(5, 15), pady=15)
        
        self.btn_install_cuda = ctk.CTkButton(self.card_cuda, text="Baixar Suporte CUDA", fg_color="#2ecc71", hover_color="#27ae60", text_color="black", command=self.install_cuda_support)
        self.btn_install_cuda.pack(side="right", padx=(5, 5), pady=15)
        
        self.btn_uninstall_cuda = ctk.CTkButton(self.card_cuda, text="🗑️ Desinstalar", fg_color="#c0392b", hover_color="#e74c3c", width=100, command=lambda: self.uninstall_module("cuda"))
        self.btn_uninstall_cuda.pack(side="right", padx=(15, 5), pady=15)

        self.log_cuda = ctk.CTkTextbox(self.card_cuda, height=80, state="disabled", fg_color="#000")

        # Card Translate
        self.card_trans = ctk.CTkFrame(self.frame_modules, fg_color="#16213e", corner_radius=10)
        self.card_trans.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(self.card_trans, text="🌍 Motor de Tradução e Polimento (IA)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.card_trans, text="Necessário para Etapas 2 e 3 (Ollama Local). Tamanho: Variável", font=ctk.CTkFont(size=12), text_color="#aaa").pack(anchor="w", padx=15, pady=(0, 10))
        
        # Model Selection for IA
        frame_model_select_corr = ctk.CTkFrame(self.card_trans, fg_color="transparent")
        frame_model_select_corr.pack(fill="x", padx=15, pady=(0, 5))
        ctk.CTkLabel(frame_model_select_corr, text="Modelo p/ Revisão RAW (Etapa 2):").pack(side="left", padx=(0, 10))
        
        available_models = ["llama3.1:8b", "gemma2:9b", "qwen2.5:14b", "mistral-nemo:12b", "aya:8b"]
        try:
            import urllib.request
            import json
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1) as response:
                data = json.loads(response.read().decode())
                fetched = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                if fetched:
                    available_models = fetched
        except Exception:
            pass
            
        # Load saved prefs
        saved_corr = None
        saved_trans = None
        if MODEL_PREFS_PATH.exists():
            try:
                import json
                with open(MODEL_PREFS_PATH, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                    saved_corr = prefs.get("corr")
                    saved_trans = prefs.get("trans")
            except:
                pass

        self.combo_model_corr = ctk.CTkComboBox(frame_model_select_corr, values=available_models, width=200, command=self.save_model_prefs)
        if saved_corr and saved_corr in available_models:
            self.combo_model_corr.set(saved_corr)
        elif "llama3.1:8b" in available_models:
            self.combo_model_corr.set("llama3.1:8b")
        else:
            self.combo_model_corr.set(available_models[0])
        self.combo_model_corr.pack(side="left")

        frame_model_select_trans = ctk.CTkFrame(self.card_trans, fg_color="transparent")
        frame_model_select_trans.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(frame_model_select_trans, text="Modelo p/ Tradução (Etapa 3):").pack(side="left", padx=(0, 24))
        
        self.combo_model_trans = ctk.CTkComboBox(frame_model_select_trans, values=available_models, width=200, command=self.save_model_prefs)
        if saved_trans and saved_trans in available_models:
            self.combo_model_trans.set(saved_trans)
        elif "mistral-nemo:12b" in available_models:
            self.combo_model_trans.set("mistral-nemo:12b")
        elif "aya:8b" in available_models:
            self.combo_model_trans.set("aya:8b")
        elif "qwen2.5:14b" in available_models:
            self.combo_model_trans.set("qwen2.5:14b")
        elif "llama3.1:8b" in available_models:
            self.combo_model_trans.set("llama3.1:8b")
        else:
            self.combo_model_trans.set(available_models[0])
        self.combo_model_trans.pack(side="left")
        frame_trans_status = ctk.CTkFrame(self.card_trans, fg_color="transparent")
        frame_trans_status.pack(fill="x")
        self.lbl_status_trans = ctk.CTkLabel(frame_trans_status, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_trans.pack(side="left", padx=15, pady=15)
        self.pb_trans = ctk.CTkProgressBar(frame_trans_status, mode="determinate", width=150)
        self.pb_trans.pack(side="left", padx=10, pady=15)
        self.pb_trans.set(0)
        
        self.btn_verify_trans = ctk.CTkButton(frame_trans_status, text="🔄 Verificar", fg_color="#444", hover_color="#555", width=100, command=self.refresh_module_status)
        self.btn_verify_trans.pack(side="right", padx=(5, 15), pady=15)
        
        def open_ollama_site():
            import webbrowser
            webbrowser.open("https://ollama.com/download/windows")
            
        self.btn_install_trans = ctk.CTkButton(frame_trans_status, text="Baixar Ollama", fg_color="#e94560", hover_color="#c0392b", command=open_ollama_site)
        self.btn_install_trans.pack(side="right", padx=(5, 5), pady=15)
        
        self.btn_pull_ollama = ctk.CTkButton(frame_trans_status, text="⬇ Puxar", fg_color="#3498db", hover_color="#2980b9", width=80, command=self.pull_ollama_model)
        self.btn_pull_ollama.pack(side="right", padx=(5, 5), pady=15)
        
        self.btn_delete_ollama = ctk.CTkButton(frame_trans_status, text="🗑️ Apagar", fg_color="#c0392b", hover_color="#e74c3c", width=80, command=self.delete_ollama_model)
        self.btn_delete_ollama.pack(side="right", padx=(15, 5), pady=15)
        
        self.log_trans = ctk.CTkTextbox(self.card_trans, height=100, state="disabled", fg_color="#000")

        # Card RAG Memory
        self.card_rag = ctk.CTkFrame(self.frame_modules, fg_color="#1a1a2e", corner_radius=10)
        self.card_rag.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(self.card_rag, text="🧠 Motor de Memória (RAG Vector DB)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.card_rag, text="Necessário para a V2. Busca semântica no histórico de traduções usando ChromaDB. Tamanho: ~1.5 GB", font=ctk.CTkFont(size=12), text_color="#aaa").pack(anchor="w", padx=15, pady=(0, 10))
        
        self.lbl_status_rag = ctk.CTkLabel(self.card_rag, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_rag.pack(side="left", padx=15, pady=15)
        self.pb_rag = ctk.CTkProgressBar(self.card_rag, mode="determinate", width=150)
        self.pb_rag.pack(side="left", padx=10, pady=15)
        self.pb_rag.set(0)
        
        self.sw_rag = ctk.CTkSwitch(self.card_rag, text="Ativar Memória de Contexto", variable=self.var_use_rag, font=ctk.CTkFont(weight="bold"), fg_color="#444", progress_color="#e94560")
        self.sw_rag.pack(side="left", padx=15, pady=15)
        
        self.btn_verify_rag = ctk.CTkButton(self.card_rag, text="🔄 Verificar", fg_color="#444", hover_color="#555", width=100, command=self.refresh_module_status)
        self.btn_verify_rag.pack(side="right", padx=(5, 15), pady=15)
        
        self.btn_install_rag = ctk.CTkButton(self.card_rag, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_rag)
        self.btn_install_rag.pack(side="right", padx=(5, 5), pady=15)
        
        self.btn_uninstall_rag = ctk.CTkButton(self.card_rag, text="🗑️ Desinstalar", fg_color="#c0392b", hover_color="#e74c3c", width=100, command=lambda: self.uninstall_module("rag"))
        self.btn_uninstall_rag.pack(side="right", padx=(15, 5), pady=15)
        
        self.log_rag = ctk.CTkTextbox(self.card_rag, height=100, state="disabled", fg_color="#000")


        self.refresh_module_status()

    def refresh_module_status(self):
        # Update Storage size
        size_str = self.calculate_models_size()
        self.lbl_storage.configure(text=f"💾 Armazenamento Ocupado pelos Modelos de IA: {size_str}")
        self.btn_pull_ollama.configure(state="normal", text="⬇ Puxar")

        # UI updates: reset all progress bars to 0 and set verifying labels
        self.lbl_status_ocr.configure(text="Status: ⏳ Verificando dependências...", text_color="#f1c40f")
        self.btn_install_ocr.configure(state="disabled")
        self.btn_verify_ocr.configure(state="disabled")
        self.pb_ocr.set(0.0)
        
        self.lbl_status_trans.configure(text="Status: ⏳ Verificando motores...", text_color="#f1c40f")
        self.btn_install_trans.configure(state="disabled")
        self.btn_verify_trans.configure(state="disabled")
        self.pb_trans.set(0.0)
        
        self.lbl_status_cuda.configure(text="Status: ⏳ Verificando hardware...", text_color="#f1c40f")
        self.pb_cuda.set(0.0)

        self.lbl_status_rag.configure(text="Status: ⏳ Verificando memória RAG...", text_color="#f1c40f")
        self.btn_install_rag.configure(state="disabled")
        self.btn_verify_rag.configure(state="disabled")
        self.pb_rag.set(0.0)

        def worker():
            import time
            def update_pb(pb, val): self.after(0, lambda: pb.set(val))

            # Verifica OCR
            update_pb(self.pb_ocr, 0.3)
            has_ocr = self.check_module_ocr()
            update_pb(self.pb_ocr, 0.8)
            time.sleep(0.1)

            # Verifica Tradução
            update_pb(self.pb_trans, 0.3)
            has_trans = self.check_module_translation()
            update_pb(self.pb_trans, 0.8)
            time.sleep(0.1)

            # Verifica RAG
            update_pb(self.pb_rag, 0.3)
            has_rag = self.check_module_rag()
            update_pb(self.pb_rag, 0.8)
            time.sleep(0.1)
            
            # Verifica CUDA
            update_pb(self.pb_cuda, 0.3)
            has_cuda = False
            if has_ocr:
                try:
                    if getattr(sys, 'frozen', False):
                        install_dir = Path(sys.executable).parent
                    else:
                        install_dir = Path(__file__).parent
                    venv_ocr_python = install_dir / "venv_ocr" / "Scripts" / "python.exe"
                    
                    creationflags = 0x08000000 if sys.platform == "win32" else 0
                    cmd = [str(venv_ocr_python), "-c", "import torch; print('CUDA_OK') if torch.cuda.is_available() else print('CUDA_FAIL')"]
                    import os
                    env = os.environ.copy()
                    env.pop("PYTHONPATH", None)
                    env.pop("PYTHONHOME", None)
                    update_pb(self.pb_cuda, 0.6)
                    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags, env=env)
                    has_cuda = "CUDA_OK" in result.stdout
                except:
                    pass
            else:
                has_cuda = False
            
            update_pb(self.pb_cuda, 0.9)
            time.sleep(0.2) # Para dar o feedback visual

            
            def update_ui():
                self.pb_ocr.set(1.0)
                if has_ocr:
                    self.lbl_status_ocr.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
                    self.btn_install_ocr.configure(state="disabled", fg_color="#444", text="Já Instalado")
                    self.btn_verify_ocr.configure(state="normal")
                    self.btn_uninstall_ocr.configure(state="normal")
                    self.pb_ocr.configure(progress_color="#2ecc71")
                else:
                    self.lbl_status_ocr.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
                    self.btn_install_ocr.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar")
                    self.btn_verify_ocr.configure(state="normal")
                    self.btn_uninstall_ocr.configure(state="disabled")
                    self.pb_ocr.set(0)

                self.pb_trans.set(1.0)
                if has_trans:
                    self.lbl_status_trans.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
                    self.btn_install_trans.configure(state="disabled", fg_color="#444", text="Já Instalado")
                    self.btn_verify_trans.configure(state="normal")
                    self.pb_trans.configure(progress_color="#2ecc71")
                else:
                    self.lbl_status_trans.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
                    self.btn_install_trans.configure(state="normal", fg_color="#e94560", text="Baixar Ollama")
                    self.btn_verify_trans.configure(state="normal")
                    self.pb_trans.set(0)
                    
                self.pb_cuda.set(1.0)
                if has_cuda:
                    self.lbl_status_cuda.configure(text="Status: ✅ Aceleração Ativa", text_color="#2ecc71")
                    self.pb_cuda.configure(progress_color="#2ecc71")
                    
                    self.switch_gpu.configure(state="normal", text="Forçar Uso da GPU no OCR (Habilitado)")
                    self.var_use_gpu.set(True)
                    self.btn_install_cuda.configure(state="disabled", text="Instalado")
                    self.btn_uninstall_cuda.configure(state="normal")
                    if hasattr(self, 'lbl_process_status_cuda'):
                        self.lbl_process_status_cuda.configure(text="GPU: ✅ Ativo", text_color="#2ecc71")
                else:
                    self.lbl_status_cuda.configure(text="Status: ❌ Aceleração Ausente", text_color="#e74c3c")
                    self.pb_cuda.set(0)
                    
                    self.switch_gpu.configure(state="disabled", text="Forçar Uso da GPU no OCR (Incompatível/Não Instalado)")
                    self.var_use_gpu.set(False)
                    self.btn_install_cuda.configure(state="normal", text="Baixar Suporte CUDA")
                    self.btn_uninstall_cuda.configure(state="disabled")
                    if hasattr(self, 'lbl_process_status_cuda'):
                        self.lbl_process_status_cuda.configure(text="GPU: ❌ Ausente", text_color="#e74c3c")
                    
                self.pb_rag.set(1.0)
                if has_rag:
                    self.lbl_status_rag.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
                    self.btn_install_rag.configure(state="disabled", fg_color="#444", text="Já Instalado")
                    self.btn_verify_rag.configure(state="normal")
                    self.btn_uninstall_rag.configure(state="normal")
                    self.pb_rag.configure(progress_color="#2ecc71")
                    self.sw_rag.configure(state="normal")
                    if hasattr(self, 'lbl_process_status_rag'):
                        self.lbl_process_status_rag.configure(text="RAG: ✅ Ativo", text_color="#2ecc71")
                else:
                    self.lbl_status_rag.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
                    self.btn_install_rag.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar")
                    self.btn_verify_rag.configure(state="normal")
                    self.btn_uninstall_rag.configure(state="disabled")
                    self.pb_rag.set(0)
                    self.sw_rag.configure(state="disabled")
                    self.var_use_rag.set(False)
                    if hasattr(self, 'lbl_process_status_rag'):
                        self.lbl_process_status_rag.configure(text="RAG: ❌ Ausente", text_color="#e74c3c")
                    
            self.after(0, update_ui)
            
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _ui_log(self, box, text):
        def _append():
            box.configure(state="normal")
            box.insert("end", text + "\n")
            box.see("end")
            box.configure(state="disabled")
        self.after(0, _append)
        
    def _bump_progress(self, pb):
        current = pb.get()
        if current < 0.95:
            pb.set(current + 0.01)

    def verify_cuda_support(self):
        """Testa se a GPU NVIDIA está disponível para o PyTorch."""
        self.btn_test_gpu.configure(state="disabled", text="⏳ Testando...")
        self.log_cuda.pack(fill="x", padx=15, pady=(0, 15))
        self.log_cuda.configure(state="normal")
        self.log_cuda.delete("1.0", "end")
        self.log_cuda.insert("end", "Iniciando teste de GPU CUDA (PyTorch)...\n")
        self.log_cuda.configure(state="disabled")

        def _run_test():
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
                
            venv_ocr_python = install_dir / "venv_ocr" / "Scripts" / "python.exe"
            
            if not venv_ocr_python.exists():
                self._ui_log(self.log_cuda, "❌ Módulo OCR Base não instalado. Baixe-o primeiro no cartão acima.")
                self.after(0, lambda: self.btn_test_gpu.configure(state="normal", text="⚡ Testar Placa de Vídeo"))
                return

            try:
                creationflags = 0x08000000 if sys.platform == "win32" else 0
                cmd = [str(venv_ocr_python), "-c", "import torch; print('CUDA_OK') if torch.cuda.is_available() else print('CUDA_FAIL')"]
                import os
                env = os.environ.copy()
                env.pop("PYTHONPATH", None)
                env.pop("PYTHONHOME", None)
                result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags, env=env)
                
                if "CUDA_OK" in result.stdout:
                    self._ui_log(self.log_cuda, "✅ SUCESSO: GPU NVIDIA detectada e pronta para o OCR!")
                    self._ui_log(self.log_cuda, "O EasyOCR rodará com aceleração total de hardware.")
                    self.after(0, self.refresh_module_status)
                else:
                    self._ui_log(self.log_cuda, "⚠️ AVISO: GPU NVIDIA (CUDA) não foi detectada pelo PyTorch.")
                    self._ui_log(self.log_cuda, "O OCR rodará em MODO LENTO (usando apenas a CPU).")
                    self._ui_log(self.log_cuda, "\nPara resolver (Apenas para placas NVIDIA):")
                    self._ui_log(self.log_cuda, "1. Clique em 'Baixar Suporte CUDA' nesta seção.")
                    self._ui_log(self.log_cuda, "2. Atualize os drivers da sua placa de vídeo pelo GeForce Experience.")
                    self._ui_log(self.log_cuda, "Nota: Placas AMD ou Intel não suportam CUDA. O modo CPU é o ideal.")
                    
            except Exception as e:
                self._ui_log(self.log_cuda, f"❌ Erro ao testar CUDA: {e}")
                
            finally:
                self.after(0, lambda: self.btn_test_gpu.configure(state="normal", text="⚡ Testar Placa de Vídeo"))

        threading.Thread(target=_run_test, daemon=True).start()

    def install_cuda_support(self):
        self.btn_install_cuda.configure(state="disabled", text="Instalando CUDA...")
        self.log_cuda.pack(fill="x", padx=15, pady=(0, 15))
        self.log_cuda.configure(state="normal")
        self.log_cuda.delete("1.0", "end")
        self.log_cuda.insert("end", "Iniciando download da Aceleração CUDA (~2.5GB). Pode demorar...\n")
        self.log_cuda.configure(state="disabled")

        def _run_install():
            if getattr(sys, 'frozen', False):
                install_dir = Path(sys.executable).parent
            else:
                install_dir = Path(__file__).parent
                
            venv_ocr_python = install_dir / "venv_ocr" / "Scripts" / "python.exe"
            
            if not venv_ocr_python.exists():
                self._ui_log(self.log_cuda, "❌ Instale o Módulo OCR Base (acima) primeiro!")
                self.after(0, lambda: self.btn_install_cuda.configure(state="normal", text="Baixar Suporte CUDA"))
                return
                
            try:
                cmd = [
                    str(venv_ocr_python), "-m", "pip", "install", 
                    "torch", "torchvision", "--pre", "--index-url", "https://download.pytorch.org/whl/nightly/cu126",
                    "--default-timeout=1000", "--force-reinstall", "--no-deps"
                ]
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=0x08000000 if sys.platform == "win32" else 0,
                    startupinfo=startupinfo
                )
                
                for line in proc.stdout:
                    if line.strip():
                        self._ui_log(self.log_cuda, line.strip())
                        self.after(0, lambda: self._bump_progress(self.pb_cuda))
                proc.wait()
                
                if proc.returncode == 0:
                    self._ui_log(self.log_cuda, "\n✅ Aceleração CUDA instalada com sucesso!")
                    self.after(0, self.refresh_module_status)
                else:
                    self._ui_log(self.log_cuda, "\n❌ Ocorreu um erro durante a instalação.")
                    
            except Exception as e:
                self._ui_log(self.log_cuda, f"\n❌ Falha grave: {e}")
            finally:
                self.after(0, lambda: self.btn_install_cuda.configure(state="normal", text="Baixar Suporte CUDA"))

        threading.Thread(target=_run_install, daemon=True).start()

    def install_ocr(self):
        self.btn_install_ocr.configure(state="disabled", text="Instalando...")
        self.log_ocr.pack(fill="x", padx=15, pady=(0, 15))
        self.log_ocr.configure(state="normal")
        self.log_ocr.delete("0.0", "end")
        self.log_ocr.configure(state="disabled")

        def worker():
            try:
                import sys
                import shutil
                import subprocess
                from pathlib import Path
                
                CREATE_NO_WINDOW = 0x08000000
                self._ui_log(self.log_ocr, "▶ Preparando ambiente isolado de OCR...")
                
                if getattr(sys, 'frozen', False):
                    install_dir = Path(sys.executable).parent
                else:
                    install_dir = Path(__file__).parent
                    
                venv_ocr_dir = install_dir / "venv_ocr"
                
                # Destrói o venv se ele já existir para garantir uma instalação limpa
                if venv_ocr_dir.exists():
                    self._ui_log(self.log_ocr, "  Apagando instalação anterior (pode demorar alguns segundos)...")
                    shutil.rmtree(venv_ocr_dir, ignore_errors=True)
                    
                self._ui_log(self.log_ocr, "  Criando venv_ocr...")
                startupinfo_venv = subprocess.STARTUPINFO()
                startupinfo_venv.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_ocr_dir)],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=startupinfo_venv
                )
                
                venv_ocr_python = venv_ocr_dir / "Scripts" / "python.exe"
                if not venv_ocr_python.exists():
                    self._ui_log(self.log_ocr, "❌ Falha ao criar ambiente virtual isolado!")
                    return
                
                req = install_dir / "requirements-ocr.txt"
                if not req.exists():
                    self._ui_log(self.log_ocr, "❌ Arquivo requirements-ocr.txt não encontrado!")
                    return

                self._ui_log(self.log_ocr, "▶ Baixando e instalando o Motor de IA (Tempo Estimado: 1 a 3 minutos)...")
                
                # Usa venv_ocr_python, remove quiet para mostrar logs
                cmd = [
                    str(venv_ocr_python), "-m", "pip", "install", "-r", str(req), 
                    "--default-timeout=1000"
                ]
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                import os
                env = os.environ.copy()
                env.pop("PYTHONPATH", None)
                env.pop("PYTHONHOME", None)
                
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=startupinfo,
                    env=env
                )
                for line in proc.stdout:
                    stripped = line.strip()
                    if stripped:
                        self._ui_log(self.log_ocr, stripped[:120])
                        self.after(0, lambda: self._bump_progress(self.pb_ocr))
                proc.wait()

                if proc.returncode == 0:
                    self._ui_log(self.log_ocr, "✅ Instalação concluída com sucesso!")
                else:
                    self._ui_log(self.log_ocr, f"❌ Erro na instalação. O download pode ter falhado.")
                    self._ui_log(self.log_ocr, "Clique em 'Baixar e Instalar' novamente para tentar continuar.")
            except Exception as e:
                self._ui_log(self.log_ocr, f"❌ Exceção: {e}")
            finally:
                self.after(0, self.refresh_module_status)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def save_model_prefs(self, _=None):
        import json
        prefs = {
            "corr": self.combo_model_corr.get(),
            "trans": self.combo_model_trans.get()
        }
        try:
            with open(MODEL_PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(prefs, f)
        except Exception as e:
            self.log(f"⚠️ Erro ao salvar preferências de modelo: {e}")

if __name__ == "__main__":
    app = MangaApp()
    app.mainloop()
