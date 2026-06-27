import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Remove the static text labels
lines_to_remove = [
    r'ctk\.CTkLabel\(self\.card_ocr,\s*text="Necessário para a Etapa 1[^)]+\)\.pack\([^)]+\)\n?',
    r'ctk\.CTkLabel\(self\.card_cuda,\s*text="Exclusivo para placas NVIDIA[^)]+\)\.pack\([^)]+\)\n?',
    r'ctk\.CTkLabel\(self\.card_trans,\s*text="Necessário para Etapas 2 e 3[^)]+\)\.pack\([^)]+\)\n?',
    r'ctk\.CTkLabel\(self\.card_rag,\s*text="Busca semântica no histórico[^)]+\)\.pack\([^)]+\)\n?'
]

for pattern in lines_to_remove:
    # Use re.sub to remove the line
    code = re.sub(pattern, '', code)

# 2. Add ToolTips to the cards instead
def inject_tooltips(match):
    return match.group(0) + """
        ToolTip(self.card_ocr, "Necessário para a Etapa 1. Florence-2-Large (GPU/CPU). Tamanho: ~2.5 GB")
        ToolTip(self.card_cuda, "Exclusivo para placas NVIDIA. Acelera drasticamente a extração OCR. Tamanho: ~2.5 GB")
        ToolTip(self.card_trans, "Necessário para Etapas 2 e 3 (Ollama Local). Tamanho: Variável")
        ToolTip(self.card_rag, "Busca semântica no histórico de traduções usando ChromaDB. Tamanho: ~1.5 GB")
"""
# Inject right after self.sw_rag.pack(...)
code = re.sub(r'self\.sw_rag\.pack\([^)]+\)', inject_tooltips, code)

# 3. Add Toast to Settings save
def inject_settings_toast(match):
    return match.group(0) + '\n        self.show_toast("Configurações Salvas e Aplicadas!")'
code = re.sub(r'ctk\.set_appearance_mode\(new_theme\)', inject_settings_toast, code)

# 4. Add Toast to Studio Save
# Look for: with open(self.studio_translated_txt_path, "w", encoding="utf-8") as f:\n            f.write(final_text)
def inject_studio_toast(match):
    return match.group(0) + '\n        self.show_toast("Tradução Salva no Estúdio!")'
code = re.sub(r'f\.write\(final_text\)', inject_studio_toast, code)

# 5. Add Toast to Reader Save
# Look for: with open(self.reader_current_file, "w", encoding="utf-8") as f:\n            f.write(final_txt)
def inject_reader_toast(match):
    return match.group(0) + '\n        self.show_toast("Arquivo Salvo com Sucesso!")'
code = re.sub(r'f\.write\(final_txt\)', inject_reader_toast, code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("UX Final Fix Applied.")
