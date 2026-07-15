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
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read().replace("\ufeff", "")

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

def correct_texts(texts: list[str], model: str, dict_content: str = "", context: str = "") -> list[str]:
    """Usa o Ollama para normalizar os textos OCR em inglês, removendo gírias e corrigindo case."""
    if not texts:
        return []

    # Auto-split em lotes para páginas com muitos balões (evita overflow de num_ctx)
    MAX_BATCH_SIZE = 8
    if len(texts) > MAX_BATCH_SIZE:
        result = []
        for batch_start in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[batch_start:batch_start + MAX_BATCH_SIZE]
            batch_result = correct_texts(
                texts=batch,
                model=model,
                dict_content=dict_content,
                context=context
            )
            result.extend(batch_result)
        return result

    dict_prompt = ""
    if dict_content:
        dict_prompt = f"\n# SFX & FALSE COGNATES TO IGNORE (Must Output [IGNORE]):\n{dict_content}\n"

    context_prompt = ""
    if context:
        context_prompt = f"\n# CONTEXT FOR CORRECTION:\n{context}\n"

    numbered_input = "\n".join([f"[{i+1}] {text}" for i, text in enumerate(texts)])

    prompt = f"""You are an expert English proofreader and normalizer preparing Manga comic OCR text for AI translation.
The following numbered lines are speech balloons extracted from a manga page. Each numbered entry is a SEPARATE balloon.

# CRITICAL NORMALIZATION RULES
1. DE-SLANG & EXPAND CONTRACTIONS (PRIORITY #1): Manga speech uses heavy slang, dropped letters, and spoken shortcuts that confuse translation AI. You MUST normalize informal slang into clear, complete standard English:
   - "didja?" / "didn'tcha?" -> "did you?" / "didn't you?"
   - "whaddaya" / "whatcha" -> "what do you" / "what are you"
   - "gonna" / "wanna" / "gotta" / "gimme" -> "going to" / "want to" / "have to" / "give me"
   - "ain't ya" / "ain't it" -> "aren't you" / "isn't it"
   - "toldja" / "y'didn't" / "y'gonna" -> "I told you" / "you didn't" / "you are going to"
   - "outta" / "kinda" / "sorta" -> "out of" / "kind of" / "sort of"
   - Dropped 'g's ("movin'", "gettin'", "somethin'", "nuthin'") -> "moving", "getting", "something", "nothing"
   - Clipped words ("'em", "'nd", "'s'kinda") -> "them", "and", "it is kind of"
2. SENTENCE CASE NORMALIZATION: Convert ALL CAPS manga text into proper Sentence case ("HELLO MY FRIEND." -> "Hello my friend.").
3. FIX OCR GLITCHES & STUTTERING: Fix scanning stutter/repeats ("I sold sold it" -> "I sold it") and misread punctuation ("StopI" -> "Stop!").
4. PRESERVE JAPANESE PROPER NOUNS: Do NOT alter Japanese proper names or places (e.g., "Harima", "Otodo", "Hanabi", "Genikasuri", "Daimon Gym"). Keep them exact.
5. ELONGATED GREETINGS: Do not change intentional vocal greetings ("Yoooo" stays "Yoooo", "Heyyy" stays "Heyyy").
6. SFX & ONOMATOPOEIA DETECTION: If a line is purely a sound effect or visual noise ('POCK!', 'GYAAA', 'BAM', '0'), output EXACTLY [IGNORE].
7. PRESERVE LINE NUMBERING: Output MUST have the EXACT SAME number of lines as input, each starting with [N].
8. NO COMMENTS: Output ONLY the normalized English text lines.

# EXAMPLES
Input:
[1] DIDN'T CATCH THAT, DIDJA?
[2] SO Y'GONNA PAY ME THE PURSE, OR WHAT?!
[3] WHADDAYA MEAN GROSS?
[4] YOU'RE MOVIN' ABOUT LIKE THAT? 'S'KINDA GROSS...
[5] TOLDJA Y'DIDN'T CATCH IT.
[6] IF I PUT ON A GOOD SHOW AND WIN YOU'LL GIMME THE PURSE MONEY YEAH?
[7] POCK!
Normalized:
[1] You didn't catch that, did you?
[2] So are you going to pay me the purse money, or what?!
[3] What do you mean gross?
[4] You are moving about like that? It is kind of gross...
[5] I told you that you didn't catch it.
[6] If I put on a good show and win, you will give me the purse money, right?
[7] [IGNORE]

{dict_prompt}{context_prompt}
# INPUT TO NORMALIZE:
{numbered_input}
"""

    max_retries = 3
    for attempt in range(max_retries):
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
                        "num_ctx": 4096
                    }
                },
                timeout=300
            )
            response.raise_for_status()
            raw = response.json().get("response", "").strip()
    
            result = list(texts)
            parsed_count = 0
    
            # --- Estratégia 1: Formato padrão numerado ---
            for match in re.finditer(r'(?:\[(\d+)\]|(\d+)[\.\:\)\-])[\s\:\-\)]*(.*?)(?=\n(?:\[\d+\]|\d+[\.\:\)\-])|$)', raw, re.DOTALL):
                idx_str = match.group(1) or match.group(2)
                if not idx_str: continue
                idx = int(idx_str) - 1
                corrected = match.group(3).strip()
                corrected = re.sub(r'^[\:\-\)\.\s]+', '', corrected).strip()
                if 0 <= idx < len(result):
                    result[idx] = corrected
                    parsed_count += 1
    
            # --- Estratégia 2: Formato "Balão [N]" com "Correto:" ---
            if parsed_count < len(result):
                balloon_blocks = re.findall(
                    r'(?:Bal[aã]o\s*\[?(\d+)\]?|\*{0,2}Bal[aã]o\s*\[?(\d+)\]?\*{0,2})'
                    r'.*?(?:Correto|Correct|Tradu[çc][ãa]o)\s*:\s*(.+?)(?=\n\n|\n\*{0,2}Bal|\Z)',
                    raw, re.DOTALL | re.IGNORECASE
                )
                for grp in balloon_blocks:
                    idx_str = grp[0] or grp[1]
                    if not idx_str: continue
                    idx = int(idx_str) - 1
                    corrected = grp[2].strip().splitlines()[0].strip()
                    if 0 <= idx < len(result) and result[idx] == texts[idx]:
                        result[idx] = corrected
                        parsed_count += 1
    
            # --- Estratégia 3: "Correto: [N] texto" ou "Correto: texto" sequencial ---
            if parsed_count < len(result):
                correto_matches = re.findall(r'(?:Correto|Correct)\s*:\s*(?:\[(\d+)\]\s*)?(.+?)(?=\n|$)', raw, re.IGNORECASE)
                if correto_matches:
                    seq_idx = 0
                    for m in correto_matches:
                        idx = int(m[0]) - 1 if m[0] else seq_idx
                        corrected = m[1].strip()
                        if 0 <= idx < len(result) and result[idx] == texts[idx]:
                            result[idx] = corrected
                            parsed_count += 1
                        seq_idx += 1
    
            # --- Estratégia 4: Fallback linha por linha ---
            if parsed_count == 0:
                lines = [l.strip() for l in raw.splitlines() if l.strip()
                         and not re.match(r'^\*+$', l.strip())
                         and not l.strip().lower().startswith(('observ', 'nota', 'tradu'))
                         ]
                if len(lines) == len(texts):
                    for idx, line in enumerate(lines):
                        clean_line = re.sub(r'^(?:\[?\d+\]?[\.\:\-\)\s]*)', '', line).strip()
                        result[idx] = clean_line
    
            return result
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"  [!] Timeout na API Ollama (Tentativa {attempt + 1}/{max_retries}). Retentando...")
                import time
                time.sleep(2)
                continue
            print(f"Erro na API Ollama: Timeout após {max_retries} tentativas")
            return texts
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [!] Erro na API Ollama (Tentativa {attempt + 1}/{max_retries}): {e}")
                import time
                time.sleep(2)
                continue
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
    
    # Cache de Auto-Mesclagem: se já existe um arquivo corrigido, não reprocessa páginas já corrigidas
    existing_fixed_map = {}
    if output_path.exists():
        try:
            ex_pages = parse_txt(output_path, None)
            for ep_name, ep_texts in ex_pages.items():
                if ep_texts and not (len(ep_texts) == 1 and "[Nenhum texto" in ep_texts[0]):
                    existing_fixed_map[ep_name] = ep_texts
            if existing_fixed_map:
                print(f"⚡ {len(existing_fixed_map)} página(s) já corrigida(s) em cache no arquivo. Mantendo intactas sem reprocessar!")
        except Exception:
            pass
    
    global_texts = []
    mapping = []
    skipped_pages = {}
    
    for page_name, texts in pages.items():
        if not texts:
            continue
            
        # Se a página já existe no arquivo anterior, aproveita o cache sem gastar tempo/tokens!
        if page_name in existing_fixed_map:
            print(f"⏭️ [Página: {page_name}]: Já corrigida em cache! Mantendo intacta.")
            skipped_pages[page_name] = existing_fixed_map[page_name]
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

        import concurrent.futures

        global_fixed = []
        
        def process_chunk(arg_tuple):
            idx, chunk = arg_tuple
            print(f"  [Lote {idx + 1}/{len(chunks)}] Disparando lote para correção simultânea...")
            # Sem o last_3 sequencial exato, passamos vazio ou o anterior caso pré-computado (vazio por simplicidade paralela)
            fixed_texts = fix_ocr_with_ollama(chunk, args.model, dict_content, "")
            return fixed_texts

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(process_chunk, enumerate(chunks)))

        for idx, fixed_texts in enumerate(results):
            global_fixed.extend(fixed_texts)
            chunk = chunks[idx]
            print(f"  [Lote {idx + 1}/{len(chunks)}] --- Resultado ---")
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
