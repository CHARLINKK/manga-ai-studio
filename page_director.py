#!/usr/bin/env python3
"""
Page Director (Step 2.5)
========================
Analisa o texto de cada página e gera uma breve nota de contexto (tom, gêneros, etc) 
usando um LLM local via Ollama. 
Realiza dupla checagem com o arquivo _raw.txt (se existir) para evitar distorções de sentido da IA Corretora.
Injeta a tag [CONTEXT]: no arquivo .txt para ser usada posteriormente pelo manga_translator.py.

Uso:
    python page_director.py texto_corrigido.txt --model llama3.1:8b
"""

import argparse
import sys
import time
from pathlib import Path
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA_API_URL = "http://localhost:11434"

DIRECTOR_PROMPT = """Você é um Diretor de Tradução de mangás. Analise os balões de fala extraídos de UMA ÚNICA PÁGINA.
Abaixo você receberá o texto RAW (bruto, extraído direto da imagem, pode ter erros) e o texto CORRIGIDO (limpo por outra IA).

Seu objetivo é fornecer uma NOTA DE CONTEXTO muito breve (1 a 3 frases) para ajudar o tradutor final:
1. Indique o TOM da cena (ex: tenso, cômico) e os possíveis GÊNEROS dos falantes (se for óbvio).
2. REVISÃO DE SENTIDO (Crucial): Verifique se o texto CORRIGIDO distorceu gravemente o sentido real do texto RAW (ex: "You Scared'a our boss" virou "You scared our boss", mudando o sentido). Se houver uma distorção grave, adicione um ALERTA na nota apontando o sentido verdadeiro para que o tradutor não erre.

ATENÇÃO:
- NÃO TRADUZA o texto.
- Escreva APENAS a nota de contexto e o alerta (se houver). Nenhuma introdução ou conclusão.

TEXTO RAW (Original com possíveis erros):
{text_raw}

TEXTO CORRIGIDO (IA Corretora):
{text_corr}"""

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="page_director",
        description="Gera notas de contexto por página e checa distorções de correção.",
    )
    parser.add_argument("input", type=str, help="Arquivo _corrigido.txt de entrada")
    parser.add_argument("-o", "--output", type=str, default=None, help="Arquivo de saída.")
    parser.add_argument("--model", type=str, default="llama3.1:8b", help="Modelo Ollama para análise.")
    return parser

def check_ollama_running() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False

def parse_ocr_file(file_path: Path) -> list[dict]:
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pages = []
    current_page = None

    for line in content.split("\n"):
        line = line.rstrip("\r")

        if line.startswith("=" * 10):
            continue

        if line.startswith("PÁGINA ") or line.startswith("PAGINA "):
            if current_page is not None:
                pages.append(current_page)
            current_page = {"header": line, "texts": [], "context": ""}
            continue

        if current_page is not None and line.startswith("[CONTEXT]:"):
            current_page["context"] = line.replace("[CONTEXT]:", "").strip()
            continue

        if current_page is not None and line.strip():
            current_page["texts"].append(line.strip())

    if current_page is not None:
        pages.append(current_page)

    return pages

def generate_context(texts_raw: list[str], texts_corr: list[str], model: str) -> str:
    if not texts_corr or all("[Nenhum texto" in t for t in texts_corr):
        return ""
        
    raw_content = "\n".join(texts_raw) if texts_raw else "(Não disponível)"
    corr_content = "\n".join(texts_corr)
    
    prompt = DIRECTOR_PROMPT.format(text_raw=raw_content, text_corr=corr_content)
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 150,
        },
    }
    
    try:
        resp = requests.post(f"{OLLAMA_API_URL}/api/generate", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"    ⚠️ Falha ao gerar contexto: {e}")
        return ""

def main():
    parser = create_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    
    # Tenta descobrir o arquivo RAW com base no nome do arquivo de entrada
    raw_path = input_path.parent / input_path.name.replace("_corrigido", "_raw")

    if not input_path.is_file():
        print(f"❌ Arquivo não encontrado: {args.input}")
        sys.exit(1)

    print("🔌 Verificando conexão com Ollama...")
    if not check_ollama_running():
        print("❌ Ollama não está rodando!")
        sys.exit(1)

    print(f"📂 Lendo arquivo corrigido: {input_path}")
    pages_corr = parse_ocr_file(input_path)
    
    pages_raw = []
    if raw_path.is_file():
        print(f"📂 Lendo arquivo RAW de referência: {raw_path}")
        pages_raw = parse_ocr_file(raw_path)
    
    # Monta dicionário para acesso fácil por cabeçalho
    raw_dict = {p["header"]: p["texts"] for p in pages_raw}
    
    print(f"🎬 Iniciando Page Director Dupla-Checagem com modelo: {args.model}")
    start_time = time.time()
    
    for idx, page in enumerate(pages_corr):
        if not page.get("texts") or (len(page["texts"]) == 1 and "[Nenhum texto" in page["texts"][0]):
            continue
            
        print(f"    [Página {idx + 1}/{len(pages_corr)}] Analisando contexto...", end="", flush=True)
        
        raw_texts = raw_dict.get(page["header"], [])
        context_note = generate_context(raw_texts, page["texts"], args.model)
        
        if context_note:
            page["context"] = context_note
            preview = context_note.replace("\n", " ")
            if len(preview) > 60: preview = preview[:60] + "..."
            print(f" -> {preview}")
        else:
            print(" -> (Sem nota gerada)")

    # Gera a saída modificada
    lines = []
    for page in pages_corr:
        lines.append("==================================================")
        lines.append(page["header"])
        lines.append("==================================================")
        lines.append("")
        
        if page.get("context"):
            clean_context = page["context"].replace("\n", " ").strip()
            lines.append(f"[CONTEXT]: {clean_context}")
            lines.append("") # FIX: Impede que a UI engula a primeira fala no bloco
            
        if page.get("texts"):
            for text in page["texts"]:
                lines.append(text)
                lines.append("")
        else:
            lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✅ Análise concluída em {time.time() - start_time:.1f}s")
    
    print("🧹 Descarregando Diretor da VRAM...")
    try:
        requests.post(f"{OLLAMA_API_URL}/api/generate", json={"model": args.model, "keep_alive": 0}, timeout=5)
    except:
        pass

if __name__ == "__main__":
    main()
