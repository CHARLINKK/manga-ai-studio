import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(".")))
from app import MangaApp

FOLDER = r"E:\Genikasuri\teste"
TXT    = r"E:\Genikasuri\teste\output_raw\009_raw.txt"

app = MangaApp()

def open_editor():
    print("[TEST] Chamando load_editor_from_pipeline...")
    app.load_editor_from_pipeline(FOLDER, TXT)
    app.after(800, check_result)

def check_result():
    print(f"[TEST] pages_text keys: {list(app.chapter_pages_text.keys())}")
    print(f"[TEST] images keys: {list(app.chapter_images_paths.keys())}")
    print(f"[TEST] current_page: {app.chapter_current_page}")
    print(f"[TEST] blocks: {len(app.blocks)}")
    for i, b in enumerate(app.blocks):
        print(f"[TEST]   Block {i}: {b.textbox.get('0.0','end-1c')[:60]!r}")

app.after(500, open_editor)
app.mainloop()
