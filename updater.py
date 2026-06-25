import sys
import os
import time
import zipfile
import urllib.request
import argparse
import subprocess
from pathlib import Path

def run_updater():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="URL of the update zip file")
    args = parser.parse_args()

    print("Manga AI Studio - Auto Updater")
    print("---------------------------------")
    print(f"Baixando atualização de: {args.url}")
    
    # Wait for main app to fully close
    print("Aguardando o programa principal fechar...")
    time.sleep(3)

    temp_zip = Path("update_temp.zip")
    try:
        urllib.request.urlretrieve(args.url, temp_zip)
        print("Download concluído. Extraindo arquivos...")
        
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            # Pega o nome da pasta raiz do repositório (ex: MangaAIStudio-main)
            root_folder = zip_ref.namelist()[0].split('/')[0]
            
            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    continue
                # Ignora arquivos fora do diretório raiz se houver
                if not file_info.filename.startswith(root_folder + "/"):
                    continue
                
                # O caminho relativo sem a pasta raiz (MangaAIStudio-main)
                rel_path = file_info.filename[len(root_folder)+1:]
                
                if not rel_path:
                    continue
                    
                target_path = Path.cwd() / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Não sobrescreve o próprio updater.py e o exe do launcher
                if target_path.name in ["updater.py", "MangaAIStudio.exe", "Setup.exe", "Manga_AI_Studio_Setup.exe"]:
                    continue
                    
                # Extrai o arquivo da memória e grava
                with zip_ref.open(file_info) as source, open(target_path, "wb") as target:
                    target.write(source.read())
                    
        print("Extração concluída!")
    except Exception as e:
        print(f"Erro durante a atualização: {e}")
        time.sleep(5)
    finally:
        if temp_zip.exists():
            temp_zip.unlink()

    print("Reiniciando Manga AI Studio...")
    launcher = Path("MangaAIStudio.exe")
    if launcher.exists():
        subprocess.Popen([str(launcher)])
    else:
        # Fallback if launcher not found, run app.py
        py_exe = Path("venv/Scripts/python.exe")
        if py_exe.exists():
            subprocess.Popen([str(py_exe), "app.py"])
            
if __name__ == "__main__":
    run_updater()
