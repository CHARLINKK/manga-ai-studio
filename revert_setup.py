import sys

content = open('setup_wizard.py', encoding='utf-8').read()

# Revert PROGRAM_FILES addition
content = content.replace('"version.json",\n    "MangaAIStudio.exe",\n    "run_studio.py"', '"version.json"')

# Revert the shortcut logic back to pythonw.exe
content = content.replace(
    'app_exe = self.install_dir / "MangaAIStudio.exe"',
    'venv_pythonw = self.install_dir / "venv_ui" / "Scripts" / "pythonw.exe"'
)
content = content.replace(
    'create_shortcut(target=app_exe, name="Manga AI Studio", icon=icon, working_dir=self.install_dir)',
    'create_shortcut(target=venv_pythonw, name="Manga AI Studio", icon=icon, arguments=str(app_py), working_dir=self.install_dir)\n            create_shortcut(target=venv_pythonw, name="Manga AI Studio", icon=icon, dest_dir=self.install_dir, arguments=str(app_py), working_dir=self.install_dir)'
)
content = content.replace(
    'if self.var_open.get() and app_exe.exists():\n            subprocess.Popen([str(app_exe)], cwd=str(self.install_dir), creationflags=subprocess.CREATE_NO_WINDOW)',
    'if self.var_open.get() and venv_pythonw.exists():\n            subprocess.Popen([str(venv_pythonw), str(app_py)], cwd=str(self.install_dir), creationflags=subprocess.CREATE_NO_WINDOW)'
)

open('setup_wizard.py', 'w', encoding='utf-8').write(content)
print('Setup wizard reverted and added second shortcut logic')
