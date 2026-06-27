import re
import shutil

shutil.copy('app.py', 'app.py.bak4')

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Inject CTkToast and ToolTip classes
ui_classes = """
class CTkToast(ctk.CTkFrame):
    def __init__(self, master, message, duration=3000, **kwargs):
        super().__init__(master, fg_color=("#333", "#222"), corner_radius=8, **kwargs)
        self.message = message
        self.duration = duration
        
        self.lbl = ctk.CTkLabel(self, text=self.message, text_color="white", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl.pack(padx=20, pady=10)
        
        self.place(relx=0.5, rely=0.9, anchor="center")
        self.after(self.duration, self.destroy)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self._id = None

    def schedule_tooltip(self, event=None):
        self._id = self.widget.after(500, self.show_tooltip)

    def show_tooltip(self):
        if self.tooltip:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = ctk.CTkToplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        self.tooltip.attributes("-topmost", True)
        
        frame = ctk.CTkFrame(self.tooltip, fg_color=("#333", "#222"), corner_radius=5)
        frame.pack(fill="both", expand=True)
        label = ctk.CTkLabel(frame, text=self.text, text_color="white", justify="left", font=ctk.CTkFont(size=12))
        label.pack(padx=10, pady=5)

    def hide_tooltip(self, event=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

"""

code = re.sub(r'(class DraggableBlock)', ui_classes + r'\1', code, count=1)

# 2. Add show_toast to MangaAIApp
toast_method = """
    def show_toast(self, message, duration=3000):
        CTkToast(self, message=message, duration=duration)
"""
code = re.sub(r'(def flush\(self\):\n\s+pass)', r'\1' + '\n' + toast_method, code, count=1)

# 3. Inject Hotkeys
hotkeys = """
        # Global Hotkeys
        self.bind("<Control-Return>", lambda e: self.action_process_queue() if self.current_tab == "Processamento" else None)
        self.bind("<Escape>", lambda e: self.cancel_processing() if self.current_tab == "Processamento" else None)
        self.bind("<F5>", lambda e: self.refresh_workspace() if self.current_tab == "Processamento" else None)
"""
# Insert after self.bind("<Down>"...) in setup_studio_tab or in __init__
# Let's insert it at the end of setup_ui()
code = re.sub(r'(self\.set_tab\("Processamento"\))', r'\1\n' + hotkeys, code, count=1)

# 4. Use Toasts in specific actions
# Settings save
code = re.sub(r'(print\("Configurações salvas e tema aplicado."\))', r'\1\n        self.show_toast("Configurações Visuais Salvas!")', code)

# Studio Save
code = re.sub(r'(print\("Texto de estúdio salvo em", self\.studio_translated_txt_path\))', r'\1\n        self.show_toast("Tradução Salva com Sucesso!")', code)

# Reader Save
code = re.sub(r'(print\("Arquivo leitor salvo em", self\.reader_current_file\))', r'\1\n        self.show_toast("Alterações Salvas no Arquivo!")', code)

# Module Uninstalls
code = re.sub(r'(self\.refresh_module_status\(\))', r'\1\n        self.show_toast(f"Ação concluída no módulo!")', code)
# Actually, the uninstall is wrapped in threading or runs directly. Let's just hook the cache clear.
code = re.sub(r'(self\.btn_clear_hf\.configure\(state="normal"\))', r'\1\n            self.show_toast("Cache de Modelos Limpo!")', code)

# 5. Add Tooltips to complex elements
# We need to find the creation of self.sw_rag and self.switch_gpu
def inject_rag_tooltip(match):
    return match.group(0) + '\n        ToolTip(self.sw_rag, "Busca no histórico de traduções passadas\\npara garantir consistência em nomes de golpes e personagens.")'
code = re.sub(r'self\.sw_rag = ctk\.CTkSwitch\([^)]+\)', inject_rag_tooltip, code)

def inject_gpu_tooltip(match):
    return match.group(0) + '\n        ToolTip(self.switch_gpu, "Usa a placa de vídeo NVIDIA para extrair o texto em\\nmilissegundos. Requer instalação do módulo CUDA.")'
code = re.sub(r'self\.switch_gpu = ctk\.CTkSwitch\([^)]+\)', inject_gpu_tooltip, code)

def inject_dict_tooltip(match):
    return match.group(0) + '\n        ToolTip(self.tb_dict_global, "Termos aqui têm prioridade absoluta na tradução.\\nEx: Kage Bunshin = Clone das Sombras")'
code = re.sub(r'self\.tb_dict_global = ctk\.CTkTextbox\([^)]+\)', inject_dict_tooltip, code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("UX features injected successfully.")
