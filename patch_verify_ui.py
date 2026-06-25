import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add progress bars to UI
old_ocr_ui = """        self.lbl_status_ocr = ctk.CTkLabel(self.card_ocr, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_ocr.pack(side="left", padx=15, pady=15)"""

new_ocr_ui = """        self.lbl_status_ocr = ctk.CTkLabel(self.card_ocr, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_ocr.pack(side="left", padx=15, pady=15)
        self.pb_ocr = ctk.CTkProgressBar(self.card_ocr, mode="indeterminate", width=150)
        self.pb_ocr.pack(side="left", padx=10, pady=15)
        self.pb_ocr.set(0)"""

code = code.replace(old_ocr_ui, new_ocr_ui)

old_trans_ui = """        self.lbl_status_trans = ctk.CTkLabel(self.card_trans, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_trans.pack(side="left", padx=15, pady=15)"""

new_trans_ui = """        self.lbl_status_trans = ctk.CTkLabel(self.card_trans, text="Status: Verificando...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status_trans.pack(side="left", padx=15, pady=15)
        self.pb_trans = ctk.CTkProgressBar(self.card_trans, mode="indeterminate", width=150)
        self.pb_trans.pack(side="left", padx=10, pady=15)
        self.pb_trans.set(0)"""

code = code.replace(old_trans_ui, new_trans_ui)

# 2. Rewrite refresh_module_status
old_refresh = """    def refresh_module_status(self):
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
            self.btn_install_trans.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar (Lento)")"""

new_refresh = """    def refresh_module_status(self):
        # UI updates: set to verifying state
        self.lbl_status_ocr.configure(text="Status: ⏳ Verificando dependências...", text_color="#f1c40f")
        self.btn_install_ocr.configure(state="disabled")
        self.btn_verify_ocr.configure(state="disabled")
        self.pb_ocr.start()
        
        self.lbl_status_trans.configure(text="Status: ⏳ Verificando motores...", text_color="#f1c40f")
        self.btn_install_trans.configure(state="disabled")
        self.btn_verify_trans.configure(state="disabled")
        self.pb_trans.start()

        def worker():
            import time
            has_ocr = self.check_module_ocr()
            has_trans = self.check_module_translation()
            time.sleep(0.5) # Para dar o feedback visual
            
            def update_ui():
                self.pb_ocr.stop()
                self.pb_ocr.set(1.0)
                if has_ocr:
                    self.lbl_status_ocr.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
                    self.btn_install_ocr.configure(state="disabled", fg_color="#444", text="Já Instalado")
                    self.btn_verify_ocr.configure(state="normal")
                    self.pb_ocr.configure(progress_color="#2ecc71")
                else:
                    self.lbl_status_ocr.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
                    self.btn_install_ocr.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar")
                    self.btn_verify_ocr.configure(state="normal")
                    self.pb_ocr.set(0)

                self.pb_trans.stop()
                self.pb_trans.set(1.0)
                if has_trans:
                    self.lbl_status_trans.configure(text="Status: ✅ Instalado", text_color="#2ecc71")
                    self.btn_install_trans.configure(state="disabled", fg_color="#444", text="Já Instalado")
                    self.btn_verify_trans.configure(state="normal")
                    self.pb_trans.configure(progress_color="#2ecc71")
                else:
                    self.lbl_status_trans.configure(text="Status: ❌ Não Instalado", text_color="#e74c3c")
                    self.btn_install_trans.configure(state="normal", fg_color="#e94560", text="Baixar e Instalar")
                    self.btn_verify_trans.configure(state="normal")
                    self.pb_trans.set(0)
                    
            self.after(0, update_ui)
            
        import threading
        threading.Thread(target=worker, daemon=True).start()"""

code = code.replace(old_refresh, new_refresh)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch UI Threading applied.")
