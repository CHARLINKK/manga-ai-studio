import re
import shutil

# Backup
shutil.copy('app.py', 'app.py.bak2')

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Contrast adjustments (undo the dirty gray from the previous script and use clean white/light-gray)
contrast_replacements = {
    '("gray90", "#111")': '("#f0f0f0", "#111")',
    '("gray85", "#222")': '("#f5f5f5", "#222")',
    '("gray80", "#333")': '("#ffffff", "#333")',
    '("gray75", "#444")': '("#e0e0e0", "#444")',
    '("gray70", "#555")': '("#cccccc", "#555")',
    '("gray85", "#1f1f1f")': '("#ffffff", "#1f1f1f")',
    '("gray80", "#2b2b2b")': '("#f9f9f9", "#2b2b2b")',
    '("#e6e6fa", "#1a1a2e")': '("#ffffff", "#1a1a2e")',
    '("#dcdcdc", "#16213e")': '("#f5f5f5", "#16213e")',
    '("#bdc3c7", "#34495e")': '("#eeeeee", "#34495e")',
    '("#95a5a6", "#2c3e50")': '("#ffffff", "#2c3e50")',
    '("gray95", "#000")': '("#ffffff", "#000")',
    '("#d4efdf", "#183A28")': '("#e9f7ef", "#183A28")',
    '("#d6eaf8", "#1B263B")': '("#ebf5fb", "#1B263B")',
    '("#444", "#aaa")': '("#666", "#aaa")',
    '("#333", "#ccc")': '("#555", "#ccc")',
    '("#222", "#ddd")': '("#444", "#ddd")',
}

for old, new in contrast_replacements.items():
    code = code.replace(old, new)

# 2. Fix the active/inactive tab buttons logic
# In set_tab(), we want the active tab to use the default accent color!
# Instead of fg_color=("#3498db", "#3498db"), we omit fg_color so it uses the theme! Wait, if it was inactive, we gave it a color. We can configure fg_color="transparent" for inactive, and restore to default for active. But CustomTkinter doesn't have an easy "restore default".
# Actually, ctk.ThemeManager.theme["CTkButton"]["fg_color"] has the default!
# Let's replace the set_tab logic directly.

def replace_tab_logic(match):
    return """        for t_name, btn in self.tab_buttons.items():
            if t_name == name:
                # Active tab gets the theme accent color
                btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], text_color=ctk.ThemeManager.theme["CTkButton"]["text_color"])
            else:
                # Inactive tab gets transparent background
                btn.configure(fg_color="transparent", text_color=("#666", "#aaa"))"""

code = re.sub(r'        for t_name, btn in self.tab_buttons\.items\(\):\n\s+if t_name == name:[\s\S]*?else:\n\s+btn\.configure[^\n]*', replace_tab_logic, code)

# 3. Strip hardcoded blue colors from CTkButton so they respect the theme
# Blue hexes: #3498db, #2980b9, #1f618d
code = re.sub(r',\s*fg_color="?#3498db"?', '', code)
code = re.sub(r',\s*hover_color="?#2980b9"?', '', code)
code = re.sub(r',\s*fg_color="?#2980b9"?', '', code)
code = re.sub(r',\s*hover_color="?#1f618d"?', '', code)

# 4. Also fix the studio canvas background to be adaptative (or just light gray in light mode)
# Since it's tk.Canvas, we can't use tuples. We will bind an event or just leave it. For now, let's change #2b2b2b to #222 just to be safe. But user wanted light contrast.
# We'll modify save_and_apply_settings to also update the canvas background!
def add_canvas_update(match):
    return match.group(0) + """
            if hasattr(self, 'canvas_studio_img'):
                self.canvas_studio_img.configure(bg="#e0e0e0" if new_theme == "Light" else "#1f1f1f")"""

code = re.sub(r'ctk\.set_appearance_mode\(new_theme\)', add_canvas_update, code)

# Also apply it in __init__
def init_canvas_update(match):
    return match.group(0) + """
        self.canvas_studio_img = tk.Canvas(self.frame_studio_img, bg="#e0e0e0" if self.app_settings.get("theme", "Dark") == "Light" else "#1f1f1f", highlightthickness=0)"""

code = re.sub(r'self\.canvas_studio_img = tk\.Canvas\(self\.frame_studio_img, bg="[^"]+", highlightthickness=0\)', init_canvas_update, code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Fixes applied successfully.")
