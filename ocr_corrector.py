import argparse
import sys
from pathlib import Path
import json
import requests

import re

def load_sfx_db() -> dict:
    try:
        base_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent
        sfx_path = base_dir / "data" / "sfx_database.json"
        if sfx_path.exists():
            with open(sfx_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao carregar sfx_database.json: {e}")
    return {}

def apply_sfx_filter(text: str, sfx_db: dict) -> str:
    if not sfx_db:
        return text
    
    original_lower = text.lower().strip()
    clean_text = re.sub(r'[^a-z0-9]', '', original_lower)
    
    if clean_text and "sfx_exact" in sfx_db and clean_text in sfx_db["sfx_exact"]:
        return "[IGNORE]"
        
    if "sfx_patterns" in sfx_db:
        for pattern in sfx_db["sfx_patterns"]:
            try:
                if re.match(pattern, original_lower) or re.match(pattern, clean_text):
                    return "[IGNORE]"
            except:
                continue
                
    return text

def parse_txt(file_path: Path, sfx_db: dict) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pages = {}
    current_page = None
    lines = content.split('\n')
    
    for line in lines:
        if line.startswith("PÁGINA "):
            parts = line.replace("PÁGINA ", "").split(":")
            if len(parts) >= 2:
                page_name = parts[1].strip()
                current_page = page_name
                pages[current_page] = []
        elif line.strip() and not line.startswith("==="):
            if current_page and line.strip() != "[Nenhum texto detectado nesta página]":
                text = line.strip()
                text = text.replace("_", "...")
                
                filtered_text = apply_sfx_filter(text, sfx_db)
                pages[current_page].append(filtered_text)
                
    return pages

def fix_ocr_with_ollama(texts: list, model: str, dict_content: str = "", previous_context: str = "") -> list:
    """Envia todos os balões de uma página de uma vez em batch."""
    if not texts:
        return texts

    dict_prompt = ""
    if dict_content.strip():
        dict_prompt = f"\nCRITICAL DICTIONARY RULES:\nYou MUST NOT 'correct' or alter any of the following terms. They are intentionally kept as is:\n{dict_content.strip()}\n"
        
    context_prompt = ""
    if previous_context.strip():
        context_prompt = f"\n[PREVIOUS CONTEXT (for continuity)]\nThe previous balloons ended with:\n{previous_context.strip()}\n"

    # Monta o bloco numerado de balões
    numbered_input = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))

    prompt = f"""You are a professional English proofreader specializing in Manga translation.
The following numbered lines are speech balloon texts extracted from a boxing and martial arts manga page using OCR.
Each numbered entry is a SEPARATE balloon.

OCR may contain:
1. Minor scanning typos (e.g., 'YO4' instead of 'YOU', '1' instead of 'I', misread punctuation)
2. Punctuation errors: The OCR frequently mistakes '...' for '_' and '!' for 'I' or 'l' (especially at the end of sentences like 'StopI' -> 'Stop!' or 'What I' -> 'What!'). Always fix these based on context.
3. MERGED BALLOONS: If a single entry contains multiple sentences that don't logically flow together, split them using || as separator.
4. GLITCHES/STUTTERING: Fix stuttering/repeated words caused by OCR reading the same area twice (e.g., 'I sold sold it' -> 'I sold it', 'FOUND FOUND' -> 'FOUND').
5. GLUED PUNCTUATION: Fix glued words and possessives (e.g., 'yonday's' -> 'yonday's', 'KARASYUYAMAP?' -> 'Karasuyama?').

CRITICAL RULE (ULTRA-CONSERVATIVE MODE):
- You MUST BE EXTREMELY CONSERVATIVE.
- Do NOT hallucinate or "guess" words. If a word looks strange (e.g., "yonday", "Genikasuri", "Yitar"), it is a JAPANESE PROPER NOUN. DO NOT change it into an English word like "yesterday" or "Genius"!
- ONLY fix visual character-level glitches (like a '4' that should be an 'A', or a '_' that should be '...').
- PRESERVE all Japanese names and proper nouns EXACTLY as they appear, fixing only their glued punctuation if needed.
- UPPERCASE NORMALIZATION: Manga OCR text is usually in ALL CAPS. You MUST convert all sentences into proper Sentence case (e.g. 'HELLO MY FRIEND.' -> 'Hello my friend.'). Preserve capitalization for names and acronyms.
- SLANG EXPANSION (GENERAL): Convert shortened words, slang, and abbreviations into their FULL proper English words so the translation AI can understand them better. Example: "'sup" -> "What's up", "nuthin" -> "nothing", "gonna" -> "going to", "kill 'em" -> "kill them", "a sec" -> "a second".
- ELONGATED WORDS & GREETINGS: Do NOT confuse elongated conversational words or greetings with typos. NEVER change "Yoooo" to "You" (it means "Yo"). NEVER change "Heey" to "He". Preserve repeated letters that indicate vocal tone (e.g., "Yoooo, Ty", "Whaaat", "Noooo").
- NEVER translate. Output ONLY corrected English text
- Output MUST have the SAME number of lines as input, each starting with [N] matching the input
- If a balloon needs splitting, use || within that line
- SFX & ONOMATOPOEIA DETECTION: Manga contains many sound effects and screams (e.g., 'Tahtah', 'Gyaaa', 'Pock!', 'Krii', 'BAM', 'Aaaah', or even 'Kill' when it's a rope creaking). If a line is purely a sound effect, visual noise ('0', '##'), or an author credit, you MUST output EXACTLY the literal tag [IGNORE] for that line. DO NOT attempt to correct them into human words.
- Do not add any notes or explanations
{dict_prompt}{context_prompt}
INPUT:
{numbered_input}

OUTPUT:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_k": 10,
                    "num_ctx": 2048
                }
            },
            timeout=300
        )
        response.raise_for_status()
        raw = response.json().get("response", "").strip()

        # Parseia as linhas numeradas da resposta
        result = list(texts)  # fallback: retorna original
        import re
        for match in re.finditer(r'(?:\[(\d+)\]|(\d+)[\.\:])\s*(.*?)(?=\n(?:\[\d+\]|\d+[\.\:])|$)', raw, re.DOTALL):
            idx_str = match.group(1) or match.group(2)
            if not idx_str: continue
            idx = int(idx_str) - 1
            corrected = match.group(3).strip()
            if 0 <= idx < len(result):
                result[idx] = corrected
        return result
    except Exception as e:
        print(f"Erro na API Ollama: {e}")
        return texts

def main():
    parser = argparse.ArgumentParser(description="Corrige o texto OCR em inglês usando o modelo LLM")
    parser.add_argument("input", help="Caminho para o arquivo .txt extraído pelo manga_ocr.py")
    parser.add_argument("-o", "--output", help="Caminho para salvar o arquivo corrigido")
    parser.add_argument("--model", default="llama3.1:8b", help="Modelo Ollama a ser usado (default: llama3.1:8b)")
    parser.add_argument("--dict-global", help="Caminho para o arquivo de dicionário global")
    parser.add_argument("--dict-local", help="Caminho para o arquivo de dicionário local")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}")
        sys.exit(1)
        
    base_name = input_path.stem.replace("_raw", "")
    
    if args.output:
        out = Path(args.output)
        if out.suffix.lower() == ".txt":
            output_path = out
        else:
            out.mkdir(parents=True, exist_ok=True)
            output_path = out / f"{base_name}_corrigido.txt"
    else:
        # Padrão: salva ao lado do arquivo de entrada em uma pasta 'output_corrigido'
        default_dir = input_path.parent / "output_corrigido"
        default_dir.mkdir(parents=True, exist_ok=True)
        output_path = default_dir / f"{base_name}_corrigido.txt"
    
    print("🤖 Carregando banco de SFX...")
    sfx_db = load_sfx_db()
    if sfx_db:
        print(f"   Banco SFX carregado com {sfx_db.get('_total_entries', '?')} entradas.")

    print("🤖 Analisando texto extraído...")
    pages = parse_txt(input_path, sfx_db)
    
    dict_content = ""
    if args.dict_global and Path(args.dict_global).exists():
        with open(args.dict_global, "r", encoding="utf-8") as f:
            dict_content += f.read() + "\n"
    if args.dict_local and Path(args.dict_local).exists():
        with open(args.dict_local, "r", encoding="utf-8") as f:
            dict_content += f.read() + "\n"
    
    if dict_content.strip():
        print("📖 Dicionários carregados e aplicados.")
    
    total_balloons = sum(len(texts) for texts in pages.values())
    print(f"   Encontrado: {len(pages)} página(s), {total_balloons} texto(s).")
    print(f"🔄 Aplicando correção IA em Lotes Globais (Modelo: {args.model})...")
    
    global_texts = []
    mapping = []
    skipped_pages = {}
    
    for page_name, texts in pages.items():
        if not texts:
            continue
            
        is_translated = any(t.startswith("[BR]:") or t.startswith("[EN]:") for t in texts)
        if is_translated:
            skipped_pages[page_name] = texts
            continue
            
        for text in texts:
            global_texts.append(text)
            mapping.append(page_name)
            
    if not global_texts:
        print("  ⚠️ Nenhum novo texto precisa ser corrigido (todos já traduzidos ou vazios).")
        global_fixed = []
    else:
        BATCH_SIZE = 50
        chunks = [global_texts[i:i + BATCH_SIZE] for i in range(0, len(global_texts), BATCH_SIZE)]
        
        print(f"  📦 Total de {len(global_texts)} balão(ões) extraídos.")
        print(f"  📦 Divididos em {len(chunks)} lote(s) global(is) de no máximo {BATCH_SIZE} balões cada.")
        print()

        global_fixed = []
        previous_context_str = ""
        for chunk_idx, chunk in enumerate(chunks):
            print(f"  [Lote {chunk_idx + 1}/{len(chunks)}] Corrigindo {len(chunk)} balõe(s)...")
            fixed_texts = fix_ocr_with_ollama(chunk, args.model, dict_content, previous_context_str)
            global_fixed.extend(fixed_texts)
            
            # Armazena os últimos 3 balões para contexto da próxima página/lote
            last_3 = fixed_texts[-3:] if len(fixed_texts) >= 3 else fixed_texts
            previous_context_str = "\n".join(last_3)
            
            for original, fixed in zip(chunk, fixed_texts):
                print(f"  [Original] -> {original}")
                print(f"  [Corrigido]-> {fixed}\n")

    # Reagrupando nas páginas
    output_lines = []
    current_page_num = 0
    
    from collections import defaultdict
    page_results = defaultdict(list)
    for fixed, page_name in zip(global_fixed, mapping):
        page_results[page_name].append(fixed)

    for page_name, texts in pages.items():
        current_page_num += 1
        output_lines.append("=" * 50)
        output_lines.append(f"PÁGINA {current_page_num}: {page_name}")
        output_lines.append("=" * 50)
        output_lines.append("")
        
        if not texts:
            output_lines.append("[Nenhum texto detectado nesta página]")
            output_lines.append("")
            continue

        fixed_texts = page_results[page_name]
        for fixed in fixed_texts:
            if fixed.strip().upper() == "[IGNORE]":
                print(f"  🗑️ Balão ignorado (Ruído/Onomatopeia) na página {current_page_num}.")
                continue
                
            if "||" in fixed:
                parts = [p.strip() for p in fixed.split("||") if p.strip()]
                print(f"  ⚡ Balões fundidos separados em {len(parts)} partes na página {current_page_num}.")
                for part in parts:
                    output_lines.append(part)
                    output_lines.append("")
            else:
                output_lines.append(fixed)
                output_lines.append("")
            
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print(f"✅ Texto 99.9% polido salvo em: {output_path}")

    # Descarrega o modelo da memoria da GPU
    try:
        requests.post("http://localhost:11434/api/generate", json={"model": args.model, "keep_alive": 0}, timeout=2)
    except:
        pass

if __name__ == "__main__":
    # Necessário para evitar UnicodeEncodeError no console do Windows
    sys.stdout.reconfigure(encoding="utf-8")
    main()
