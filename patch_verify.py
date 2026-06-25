import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace OCR button
old_ocr_btn = """        self.btn_install_ocr = ctk.CTkButton(self.card_ocr, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_ocr)
        self.btn_install_ocr.pack(side="right", padx=15, pady=15)"""

new_ocr_btn = """        self.btn_verify_ocr = ctk.CTkButton(self.card_ocr, text="🔄 Verificar", fg_color="#444", hover_color="#555", width=100, command=self.refresh_module_status)
        self.btn_verify_ocr.pack(side="right", padx=(5, 15), pady=15)
        self.btn_install_ocr = ctk.CTkButton(self.card_ocr, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_ocr)
        self.btn_install_ocr.pack(side="right", padx=(15, 5), pady=15)"""

code = code.replace(old_ocr_btn, new_ocr_btn)

# Replace Trans button
old_trans_btn = """        self.btn_install_trans = ctk.CTkButton(self.card_trans, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_translation)
        self.btn_install_trans.pack(side="right", padx=15, pady=15)"""

new_trans_btn = """        self.btn_verify_trans = ctk.CTkButton(self.card_trans, text="🔄 Verificar", fg_color="#444", hover_color="#555", width=100, command=self.refresh_module_status)
        self.btn_verify_trans.pack(side="right", padx=(5, 15), pady=15)
        self.btn_install_trans = ctk.CTkButton(self.card_trans, text="Baixar e Instalar", fg_color="#e94560", hover_color="#c0392b", command=self.install_translation)
        self.btn_install_trans.pack(side="right", padx=(15, 5), pady=15)"""

code = code.replace(old_trans_btn, new_trans_btn)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Verify buttons added.")
