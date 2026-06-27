import re
import shutil

# Backup app.py
shutil.copy('app.py', 'app.py.bak')

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Smart replacements for specific color keywords to CTk tuples (Light, Dark)
# Tuple format: ("light_color", "dark_color")
replacements = {
    # Backgrounds and Frames
    '"#111"': '("gray90", "#111")',
    '"#222"': '("gray85", "#222")',
    '"#333"': '("gray80", "#333")',
    '"#444"': '("gray75", "#444")',
    '"#555"': '("gray70", "#555")',
    '"#1f1f1f"': '("gray85", "#1f1f1f")',
    '"#2b2b2b"': '("gray80", "#2b2b2b")',
    '"#1a1a2e"': '("#e6e6fa", "#1a1a2e")', 
    '"#16213e"': '("#dcdcdc", "#16213e")',
    '"#34495e"': '("#bdc3c7", "#34495e")',
    '"#2c3e50"': '("#95a5a6", "#2c3e50")',
    '"#000"': '("gray95", "#000")',
    '"#183A28"': '("#d4efdf", "#183A28")', 
    '"#1B263B"': '("#d6eaf8", "#1B263B")',
    
    # Texts
    '"#aaa"': '("#444", "#aaa")',
    '"#ccc"': '("#333", "#ccc")',
    '"#ddd"': '("#222", "#ddd")',
    '"#fff"': '("#000", "#fff")',
    '"#ffffff"': '("#000", "#ffffff")',
    '"#777"': '("#666", "#777")',
    '"#888"': '("#555", "#888")',
    '"#77CC99"': '("#1e8449", "#77CC99")',
    '"#88AADD"': '("#2874a6", "#88AADD")',
}

attributes = ["fg_color", "bg_color", "hover_color", "text_color", "border_color", "progress_color"]

for old, new in replacements.items():
    for attr in attributes:
        # Match exactly attr="#xxx" or attr = "#xxx"
        # We use re.escape to handle the exact strings safely
        pattern = attr + r'\s*=\s*' + re.escape(old)
        replacement = attr + "=" + new
        code = re.sub(pattern, replacement, code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Color sweep complete.")
