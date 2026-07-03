from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Adiciona o diretório pai (projeto principal) ao sys.path para conseguirmos importar as lógicas atuais
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

app = FastAPI(title="Manga AI Studio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # No Electron, as chamadas podem vir de localhost ou file://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "Backend do Manga AI Studio está rodando!"}

if __name__ == "__main__":
    print("Iniciando servidor FastAPI na porta 5000...", flush=True)
    # Rodar via Uvicorn na porta 5000
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
