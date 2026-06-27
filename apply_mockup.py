import re
import shutil

# Backup
shutil.copy('app.py', 'app.py.bak3')

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add borders and change fg_color for Modules and Settings Cards to make them look like the mockup
cards = ["card_storage", "card_ocr", "card_cuda", "card_trans", "card_rag", "card_theme"]

for card in cards:
    # Find the creation line of the card
    # e.g. self.card_ocr = ctk.CTkFrame(..., fg_color=..., corner_radius=10)
    # or card_theme = ctk.CTkFrame(...)
    pattern = r'(' + card + r'\s*=\s*ctk\.CTkFrame\([^)]*fg_color=)\([^)]+\)([^)]*\))'
    # We want to change the fg_color to transparent in light mode or very light, and add border
    replacement = r'\1("#fcfcfc", "#2b2b2b"), border_width=1, border_color=("#cccccc", "#444")\2'
    code = re.sub(pattern, replacement, code)
    
    # Handle cases where fg_color is a simple string like "#ffffff" instead of a tuple
    pattern2 = r'(' + card + r'\s*=\s*ctk\.CTkFrame\([^)]*fg_color=)"[^"]+"([^)]*\))'
    replacement2 = r'\1("#fcfcfc", "#2b2b2b"), border_width=1, border_color=("#cccccc", "#444")\2'
    code = re.sub(pattern2, replacement2, code)

# 2. Make workspace list items transparent so they don't look like bulky blocks in light mode
# Find: frame = ctk.CTkFrame(self.workspace_list, fg_color=("#f5f5f5" ...), corner_radius=5)
pattern_ws = r'(frame\s*=\s*ctk\.CTkFrame\(self\.workspace_list,\s*fg_color=)[^,]+(,\s*corner_radius=5\))'
code = re.sub(pattern_ws, r'\1"transparent"\2', code)

# Wait, if they are transparent, hover effect might not exist unless we add it, but that's fine.

# 3. Textboxes inside cards should be transparent or match the card
# log_ocr, log_cuda, log_trans, log_rag, log_theme
pattern_log = r'(self\.log_[a-z]+\s*=\s*ctk\.CTkTextbox\([^)]*fg_color=)"[^"]+"([^)]*\))'
code = re.sub(pattern_log, r'\1("transparent", "#111")\2', code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Mockup UI changes applied.")
