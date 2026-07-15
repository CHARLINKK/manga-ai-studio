#!/usr/bin/env python3
"""
Manga Translator
================
Traduz texto extraído de mangá (EN → PT-BR) usando LLM local via Ollama.
Lê o .txt gerado pelo manga_ocr.py e produz um .txt traduzido.

Uso:
    python manga_translator.py texto_extraido.txt
    python manga_translator.py texto.txt -o traduzido.txt --model gemma3:4b
    python manga_translator.py texto.txt --context "mangá de boxe, protagonista é o Harry"
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Força encoding UTF-8 no Windows para suportar emojis no console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# URL padrão da API do Ollama
OLLAMA_API_URL = "http://localhost:11434"

TRANSLATION_PROMPT = """Você é um localizador profissional de mangás de ação, traduzindo do INGLÊS para o PORTUGUÊS BRASILEIRO (PT-BR).
Os textos fornecidos são balões de fala extraídos de uma página. Cada linha numerada [1], [2], etc., representa um balão separado.

# REGRAS E NATURALIDADE DO PORTUGUÊS BRASILEIRO (ANTI-ENGESSAMENTO)
1. ZERO ALUCINAÇÕES (CRÍTICO): Você NUNCA deve inventar palavras que não existem no dicionário brasileiro.
2. DIÁLOGO DE MANGÁ VIVO (ANTI-DUBLAGEM): Evite tom de "dublagem antiga de TV". Escreva diálogos com o ritmo natural do português falado brasileiro contemporâneo.
   - OMITA PRONOMES DESNECESSÁRIOS: Em inglês toda frase usa "I/You". Em PT-BR, prefira ocultar o sujeito para soar natural ("Quer lutar?" em vez de "Você quer lutar?", "Tô pronto" em vez de "Eu estou pronto").
   - IMPERATIVOS NATURAIS: Para personagens informais ou em combate, use "Cala a boca!", "Vem!", "Fala!" em vez do formal "Cale a boca!", "Venha!", "Fale!".
3. ADAPTAÇÃO DE INTERJEIÇÕES E CLICHÊS DO INGLÊS: Nunca traduza expressões idiomáticas ao pé da letra:
   - "What the hell? / What the..." → "Que merda é essa?" / "Que porra é essa?" / "Mas o quê?!" (NUNCA use "O que diabos?")
   - "Are you kidding me?" → "Tá de sacanagem?" / "Tá brincando?" (NUNCA use "Você está brincando comigo?")
   - "Come on!" (em combate/provocação) → "Pode vir!" / "Bora!" / "Vem logo!" (NUNCA use "Vamos lá!")
   - "Damn it / Crap" → "Merda!" / "Porra!" / "Droga!" (NUNCA use "Maldição!")
4. GRAMÁTICA BRASILEIRA E COLOQUIALISMO (PT-BR PURO): Atenção extrema aos verbos. Nunca use construções erradas ("se eu fazer" -> "se eu fizer"). PROIBIDO usar conjugações do Português Europeu como "ouviste?", "percebeste?", "tu fizeste". Em PT-BR, use "não ouviu direito, foi?", "não pegou essa, né?", "ouviu?".
4. TRADUÇÃO OBRIGATÓRIA DE TÍTULOS E VOCATIVOS (ANTI-ANGLICISMO): Palavras como "KID" (garoto/moleque), "COACH" (treinador), "BOSS" (chefe), "OLD MAN" (velho/coroa), "BOY" (menino) NÃO SÃO NOMES PRÓPRIOS! Elas DEVEM ser obrigatoriamente traduzidas para o português (ex: "TELL ME KID!" → "DIZ AÍ, GAROTO!" ou "ME FALA, MOLEQUE!", "COACH DAN!" → "TREINADOR DAN!"). Preserve apenas nomes de pessoas reais (ex: Harima, Dan, Otodo) e sufixos japoneses (-san, -kun, -sama).
5. REGRA DE CÓPIA ZERO: Você JAMAIS deve retornar a frase exatamente igual ao inglês. Se o original tem uma frase em inglês, o seu output [BR] DEVE estar obrigatoriamente traduzido.
6. CONTINUIDADE DOS BALÕES: Se uma frase for cortada pela metade em um balão e continuar no próximo, traduza a frase como um todo e divida a tradução mantendo o sentido e a gramática. Não traduza metades de frases como sentenças independentes.
7. ONOMATOPEIAS E RUÍDOS: Se a frase for puramente um ruído, grito ou efeito sonoro (ex: "POCK!", "GYAAA", "BAM", "Tahtah"), responda EXATAMENTE com a tag literal `[IGNORE]`.
8. ANTI-CENSURA: O texto pertence a uma obra adulta. Traduza xingamentos, temas sensíveis e violência usando os equivalentes corretos e realistas do português. Não suavize as palavras.
9. SEM NOTAS DO TRADUTOR: Retorne APENAS as traduções, com a MESMA numeração de entrada (ex: [1] Texto traduzido). NUNCA adicione "Nota do Tradutor" ou explicações.
10. GÊNERO NEUTRO: Se o gênero do falante/sujeito não estiver óbvio no texto ou no contexto visual, use construções neutras para evitar errar o sexo do personagem (ex: "Alguém chegou" em vez de "Ele chegou").
11. TOLERÂNCIA A ERROS DE OCR: Se a frase original em inglês contiver repetições ou erros tipográficos causados por falhas de OCR (ex: "I sold sold it"), ignore a duplicação e traduza o sentido real de forma limpa.

# EXEMPLOS DE LOCALIZAÇÃO (Siga este padrão)
Original: "TELL ME KID!"
Correto: "DIZ AÍ, GAROTO!"

Original: "DIDN'T CATCH THAT, DIDJA?"
Correto: "Não ouviu direito, né?"

Original: "COACH DAAAN!"
Correto: "TREINADOR DAAAN!"

Original: "PURSE MONEY ?"
Correto: "DINHEIRO DA BOLSA?"

Original: "I sold sold it to them."
Correto: "Eu vendi para eles."

Original: "NICE 'ND FIRED UP!"
Correto: "Animado e com sangue nos olhos!"

Original: "FIST-FIGHTS BETWEEN GENTLEMEN..."
Correto: "Lutas de punhos entre cavalheiros..."

Original: "Tahtah tahtan!"
Correto: [IGNORE]

Original:
[1] GOTTA KILL 'EM
[2] REAL QUICK!
Correto:
[1] TENHO QUE ACABAR COM ELES
[2] BEM RÁPIDO!

{dict_section}

{context_section}
# TEXTOS PARA TRADUZIR:
{text}"""


def create_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog="manga_translator",
        description="Traduz texto de mangá (EN → PT-BR) usando Ollama local.",
        epilog="Exemplo: python manga_translator.py output/capitulo-01.txt --model gemma3:4b",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input",
        type=str,
        help="Arquivo .txt gerado pelo manga_ocr.py",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Arquivo .txt traduzido de saida. Padrao: <input>_traduzido.txt",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama3.1:8b",
        help="Modelo Ollama para traducao. Padrao: llama3.1:8b",
    )
    parser.add_argument(
        "--context",
        type=str,
        default=None,
        help="Contexto extra para a traducao (ex: 'manga de boxe, protagonista Harry')",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Temperatura do modelo (0.0=preciso, 1.0=criativo). Padrao: 0.3",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostra detalhes do processamento.",
    )
    parser.add_argument(
        "--bilingual",
        action="store_true",
        help="Exporta o texto original em ingles junto com a traducao PT-BR.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Força re-tradução ignorando páginas já traduzidas em cache.",
    )
    parser.add_argument(
        "--dict-global",
        type=str,
        default=None,
        help="Arquivo dicionario.json global",
    )
    parser.add_argument(
        "--dict-local",
        type=str,
        default=None,
        help="Arquivo dicionario.json local da pasta",
    )
    parser.add_argument(
        "--tone",
        type=str,
        default="casual e natural",
        help="Tom da tradução (ex: Shounen, Formal, Maduro).",
    )
    parser.add_argument(
        "--rag-workspace",
        type=str,
        default=None,
        help="Caminho do workspace para buscar a Memória de Tradução (ChromaDB).",
    )

    return parser


def check_ollama_running() -> bool:
    """Verifica se o Ollama está rodando."""
    try:
        resp = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def check_model_available(model: str) -> bool:
    """Verifica se o modelo está disponível no Ollama."""
    try:
        resp = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]
            # Checa com e sem tag :latest
            return model in model_names or f"{model}:latest" in model_names
        return False
    except requests.ConnectionError:
        return False


def load_false_cognates_db() -> dict:
    try:
        base_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent
        path = base_dir / "data" / "false_cognates_en_pt.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao carregar false_cognates_en_pt.json: {e}")
    return {}

def get_relevant_cognates(texts: list[str], db: dict) -> str:
    if not db: return ""
    import re
    combined_text = " ".join(texts).lower()
    relevant_rules = []
    
    if "false_cognates" in db:
        for en_word, data in db["false_cognates"].items():
            if re.search(r'\b' + re.escape(en_word.lower()) + r'\b', combined_text):
                relevant_rules.append(f"- '{en_word}' NUNCA significa '{data.get('wrong_pt', '')}'. Traduza como '{data.get('correct_pt', '')}'.")
                
    if "expression_corrections" in db:
        for en_exp, data in db["expression_corrections"].items():
            if en_exp.lower() in combined_text:
                relevant_rules.append(f"- Expressão '{en_exp}' NUNCA deve ser '{data.get('wrong_pt', '')}'. Traduza como '{data.get('correct_pt', '')}'.")

    if "manga_specific" in db:
        for en_term, data in db["manga_specific"].items():
            if re.search(r'\b' + re.escape(en_term.lower()) + r'\b', combined_text):
                relevant_rules.append(f"- Contexto Mangá: '{en_term}' NUNCA deve ser '{data.get('wrong_pt', '')}'. Use '{data.get('correct_pt', '')}'.")
                
    if not relevant_rules:
        return ""
    return "ATENÇÃO A ESTES FALSOS COGNATOS E EXPRESSÕES PRESENTES NO TEXTO:\n" + "\n".join(relevant_rules) + "\n\n"


def load_manga_dialogue_db() -> dict:
    try:
        base_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent
        path = base_dir / "data" / "manga_dialogue_localization.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao carregar manga_dialogue_localization.json: {e}")
    return {}


def get_relevant_dialogue_rules(texts: list[str], db: dict) -> str:
    if not db: return ""
    import re
    combined_text = " " + " ".join(texts).lower() + " "
    relevant_rules = []
    
    for category_key, items in db.items():
        if not isinstance(items, dict):
            continue
        for en_phrase, data in items.items():
            pattern = r'\b' + re.escape(en_phrase.lower()) + r'\b'
            if re.search(pattern, combined_text):
                corrects = " ou ".join(f'"{c}"' for c in data.get("correct_pt", []))
                wrongs = ", ".join(f'"{w}"' for w in data.get("wrong_pt", []))
                rule_line = f"- '{en_phrase.upper()}': Traduza com naturalidade como {corrects} (EVITE {wrongs})"
                if "note" in data:
                    rule_line += f" [{data['note']}]"
                relevant_rules.append(rule_line)
                
    if not relevant_rules:
        return ""
    return "LOCALIZAÇÃO NATURAL DE DIÁLOGO DE MANGÁ (GUIA COLOQUIAL PARA AS EXPRESSÕES DETECTADAS):\n" + "\n".join(relevant_rules) + "\n\n"

def post_filter_translation(original: str, translated: str) -> str:
    import re

    # 1. Remove notas de tradutor e comentários do modelo no final
    translated = re.sub(r'\n*(?:Nota do Tradutor|Nota|Note|N\.T\.?|Observa[çc][õo]es?|Lembre-se):.*$', '', translated, flags=re.IGNORECASE | re.DOTALL)

    # 2. Se o texto contém quebras de linha COM marcadores de modelo, pega só a 1ª linha válida
    if '\n' in translated:
        # Detecta se é um bloco de análise do modelo (contém "Original:", "Correto:", "Balão" etc)
        is_model_block = bool(re.search(r'(?:Original|Correto|Bal[aã]o|Tradu[çc][aã]o)\s*:', translated, re.IGNORECASE))
        if is_model_block:
            # Extrai só o campo "Correto:" / "Tradução:" se existir dentro do bloco
            correto_match = re.search(r'(?:Correto|Correct|Tradu[çc][aã]o)\s*:\s*(.+?)(?:\n|$)', translated, re.IGNORECASE)
            if correto_match:
                translated = correto_match.group(1).strip()
            else:
                # Pega a primeira linha não-vazia que não seja cabeçalho
                lines = [l.strip() for l in translated.splitlines() if l.strip()
                         and not re.match(r'^(?:Original|Correto|Bal[aã]o|\*+|Tradu[çc])', l.strip(), re.IGNORECASE)]
                translated = lines[0] if lines else original
        else:
            # 2b. Texto multi-linha sem marcadores de análise: trunca na linha onde começa
            # outro balão numerado (ex: "\nNem fodendo!\n\n[2] Animado e com...")
            numbered_continuation = re.search(r'\n\[?\d+\]?\s+', translated)
            if numbered_continuation:
                translated = translated[:numbered_continuation.start()].strip()
            else:
                # Qualquer multi-linha simples: pega só a 1ª linha não-vazia
                first_lines = [l.strip() for l in translated.splitlines() if l.strip()]
                translated = first_lines[0] if first_lines else translated

    # 3. Remove asteriscos de markdown bold/italic (**texto** -> texto)
    translated = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', translated)
    translated = re.sub(r'\*+', '', translated)

    # 4. Remove prefixos como "[1]", "1.", "Tradução:" que sobram na linha final
    translated = re.sub(r'^(?:\[?\d+\]?[\.\:\-\)\s]+|(?:Correto|Tradu[çc][aã]o)\s*:\s*)', '', translated, flags=re.IGNORECASE).strip()

    # 5. Fallback: se o resultado ainda parece inglês (idêntico ao original), marca para revisão
    original_clean = re.sub(r'[^a-z0-9]', '', original.lower())
    translated_clean = re.sub(r'[^a-z0-9]', '', translated.lower())

    if original_clean and translated_clean and translated.strip().upper() != "[IGNORE]":
        if original_clean == translated_clean:
            return translated + " [! REVISAR: MANTIDO EM INGLÊS !]"

    return translated.strip()

def translate_texts(
    texts: list[str],
    model: str,
    context: str | None = None,
    dict_content: str = "",
    temperature: float = 0.3,
    tone: str = "casual e natural",
    rag_workspace: Path | None = None,
    page_context: str = "",
    raw_texts: list[str] | None = None,
    prev_page_context: str = "",
) -> list[str]:
    """Traduz uma lista de textos em lote usando o Ollama."""
    if not texts:
        return []

    # Auto-split em lotes para páginas com muitos balões (evita overflow de num_ctx)
    MAX_BATCH_SIZE = 8
    if len(texts) > MAX_BATCH_SIZE:
        result = []
        for batch_start in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[batch_start:batch_start + MAX_BATCH_SIZE]
            batch_raw = raw_texts[batch_start:batch_start + MAX_BATCH_SIZE] if raw_texts else None
            batch_result = translate_texts(
                texts=batch,
                model=model,
                context=context,
                dict_content=dict_content,
                temperature=temperature,
                tone=tone,
                rag_workspace=rag_workspace,
                page_context=page_context,
                raw_texts=batch_raw,
                prev_page_context=prev_page_context,
            )
            result.extend(batch_result)
        return result

    context_section = ""
    if context:
        context_section += f"Contexto da obra: {context}\n\n"
        
    cognates_db = load_false_cognates_db()
    cognates_section = get_relevant_cognates(texts, cognates_db)
    if cognates_section:
        context_section += cognates_section

    dialogue_db = load_manga_dialogue_db()
    dialogue_section = get_relevant_dialogue_rules(texts, dialogue_db)
    if dialogue_section:
        context_section += dialogue_section

    if prev_page_context:
        context_section += f"CONTINUIDADE NARRATIVA (ÚLTIMAS FALAS TRADUZIDAS DA PÁGINA ANTERIOR):\n{prev_page_context}\n(Mantenha a coerência de pronomes, tratamento e tom com a página anterior)\n\n"
        
    if page_context:
        context_section += f"DIREÇÃO DE CENA DA PÁGINA (PAGE DIRECTOR):\n{page_context}\n\n"

    if raw_texts and len(raw_texts) == len(texts):
        raw_lines = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(raw_texts))
        context_section += f"REFERÊNCIA DE ESTILO ORIGINAL OCR RAW (Consulte apenas para capturar a atitude, informalidade e gírias da fala):\n{raw_lines}\n\n"
        
    if rag_workspace:
        try:
            import sys
            if str(rag_workspace) not in sys.path:
                sys.path.append(str(rag_workspace))
            import rag_memory
            
            rag_hits = []
            for i, text in enumerate(texts):
                match_br = rag_memory.query_memory(rag_workspace, text, threshold=0.3)
                if match_br:
                    rag_hits.append(f"[{i+1}] Original: '{text}' -> Tradução Histórica Obrigatória: '{match_br}'")
            
            if rag_hits:
                context_section += "ATENÇÃO: Use EXATAMENTE as seguintes traduções para as linhas listadas, pois elas vieram da Memória de Tradução (Histórico do usuário):\n"
                context_section += "\n".join(rag_hits) + "\n\n"
        except Exception as e:
            print(f"    ⚠️ Falha ao consultar Memória RAG: {e}")

    dict_section = ""
    if dict_content.strip():
        dict_section = f"DICIONÁRIO OBRIGATÓRIO (NÃO ALTERE ESTES TERMOS):\n{dict_content.strip()}\n"

    numbered_input = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))

    prompt = TRANSLATION_PROMPT.format(
        tone=tone,
        context_section=context_section,
        dict_section=dict_section,
        text=numbered_input,
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 2048,
            "num_ctx": 4096,
        },
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json=payload,
                timeout=300, # Aumentado para suportar páginas inteiras
            )
            resp.raise_for_status()
            result = resp.json()
            raw_output = result.get("response", "").strip()
            
            # Parseia as linhas numeradas da resposta
            translated = list(texts)  # Inicializa com os originais como fallback
            import re
            parsed_count = 0
    
            # --- Estratégia 1: Formato padrão numerado ---
            # Suporta [1] texto, 1. texto, 1) texto, 1: texto, [1] - texto
            for match in re.finditer(r'(?:\[(\d+)\]|(\d+)[\.\:\)\-])[\s\:\-\)]*(.*?)(?=\n(?:\[\d+\]|\d+[\.\:\)\-])|$)', raw_output, re.DOTALL):
                idx_str = match.group(1) or match.group(2)
                if not idx_str: continue
                idx = int(idx_str) - 1
                translation = match.group(3).strip()
                translation = re.sub(r'^[\:\-\)\.\s]+', '', translation).strip()
                if 0 <= idx < len(translated):
                    translated[idx] = post_filter_translation(texts[idx], translation)
                    parsed_count += 1
    
            # --- Estratégia 2: Formato "Balão [N]" com "Correto:" (llama3.1 não-padrão) ---
            # Ex: **Balão [1]**\nOriginal: ...\nCorreto: tradução\n\n**Balão [2]**\n...
            if parsed_count < len(translated):
                balloon_blocks = re.findall(
                    r'(?:Bal[aã]o\s*\[?(\d+)\]?|\*{0,2}Bal[aã]o\s*\[?(\d+)\]?\*{0,2})'
                    r'.*?(?:Correto|Correct|Tradu[çc][ãa]o)\s*:\s*(.+?)(?=\n\n|\n\*{0,2}Bal|\Z)',
                    raw_output, re.DOTALL | re.IGNORECASE
                )
                for grp in balloon_blocks:
                    idx_str = grp[0] or grp[1]
                    if not idx_str: continue
                    idx = int(idx_str) - 1
                    translation = grp[2].strip().splitlines()[0].strip()  # só 1ª linha do Correto
                    if 0 <= idx < len(translated) and translated[idx] == texts[idx]:
                        translated[idx] = post_filter_translation(texts[idx], translation)
                        parsed_count += 1
    
            # --- Estratégia 3: "Correto: [N] texto" ou "Correto: texto" sequencial (gap-filler) ---
            if parsed_count < len(translated):
                correto_matches = re.findall(r'(?:Correto|Correct)\s*:\s*(?:\[(\d+)\]\s*)?(.+?)(?=\n|$)', raw_output, re.IGNORECASE)
                if correto_matches:
                    seq_idx = 0
                    for m in correto_matches:
                        if m[0]:
                            idx = int(m[0]) - 1
                        else:
                            idx = seq_idx
                        translation = m[1].strip()
                        if 0 <= idx < len(translated) and translated[idx] == texts[idx]:
                            translated[idx] = post_filter_translation(texts[idx], translation)
                            parsed_count += 1
                        seq_idx += 1
    
            # --- Estratégia 4: Fallback linha por linha (N linhas = N balões) ---
            if parsed_count == 0:
                lines = [l.strip() for l in raw_output.splitlines() if l.strip()
                         and not re.match(r'^\*+$', l.strip())
                         and not l.strip().lower().startswith(('observ', 'nota', 'tradu'))
                         ]
                if len(lines) == len(texts):
                    for idx, line in enumerate(lines):
                        clean_line = re.sub(r'^(?:\[?\d+\]?[\.\:\-\)\s]*)', '', line).strip()
                        translated[idx] = post_filter_translation(texts[idx], clean_line)
                    
            return translated
        except requests.ConnectionError:
            print("  ❌ Erro: Ollama nao esta rodando. Inicie com 'ollama serve'.")
            import sys
            sys.exit(1)
        except requests.Timeout:
            if attempt < max_retries - 1:
                print(f"  [!] Timeout no Ollama (Tentativa {attempt + 1}/{max_retries}). Retentando...")
                import time
                time.sleep(2)
                continue
            return ["[ERRO: Timeout na traducao]"] * len(texts)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [!] Erro no Ollama (Tentativa {attempt + 1}/{max_retries}): {e}")
                import time
                time.sleep(2)
                continue
            return [f"[ERRO: {e}]"] * len(texts)


def parse_ocr_file(file_path: Path) -> list[dict]:
    """
    Lê o arquivo .txt do OCR e extrai as páginas e textos.
    
    Retorna lista de dicts:
    [{"header": "PÁGINA 1: 017.jpg", "texts": ["texto1", "texto2"]}, ...]
    """
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read().replace("\ufeff", "")

    pages = []
    current_page = None

    for line in content.split("\n"):
        line = line.rstrip("\r")

        # Detecta separadores de página
        if line.startswith("=" * 10):
            continue

        # Detecta header de página
        if line.startswith("PÁGINA ") or line.startswith("PAGINA "):
            if current_page is not None:
                pages.append(current_page)
            current_page = {"header": line, "texts": [], "context": ""}
            continue

        # Detecta contexto visual da página
        if current_page is not None and line.startswith("[CONTEXT]:"):
            current_page["context"] = line.replace("[CONTEXT]:", "").strip()
            continue

        if current_page is not None and line.strip():
            stripped = line.strip()
            # Suporte a formato bilíngue: lê somente o lado [EN]: (fonte a traduzir)
            # Ignora linhas [BR]: (já são traduções, não fonte)
            if stripped.upper().startswith("[BR]:"):
                continue
            if stripped.upper().startswith("[EN]:"):
                text = stripped[5:].strip()
                if text:  # só adiciona se houver conteúdo real após [EN]:
                    current_page["texts"].append(text)
                continue
            # Linha de texto simples (formato _corrigido.txt)
            current_page["texts"].append(stripped)

    # Última página
    if current_page is not None:
        pages.append(current_page)

    return pages


def _sanitize_translation_line(text: str) -> str:
    """Remove vazamentos de comentários do modelo em linhas de tradução individuais."""
    import re
    # Remove linhas de comentário do modelo que vazaram
    commentary_pattern = re.compile(
        r'(?:Lembre-se|Observa[çc][õo]es?|Explicação|Nota do Tradutor|Nota\b|Note\b|N\.T\.?).*',
        re.IGNORECASE | re.DOTALL
    )
    text = commentary_pattern.sub('', text).strip()
    # Remove markdown bold/italic residual
    text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)
    text = re.sub(r'\*+', '', text)
    # Remove numeração solta no início (ex: "[2] Prove..." que sobrou de parse parcial)
    text = re.sub(r'^\[\d+\]\s*', '', text).strip()
    return text


def generate_translated_output(
    pages: list[dict],
    output_path: Path,
) -> None:
    """Gera o arquivo .txt traduzido mantendo a estrutura de páginas."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for page in pages:
        separator = "=" * 50
        lines.append(separator)
        lines.append(page["header"])
        lines.append(separator)
        lines.append("")

        if page.get("translations"):
            for translation in page["translations"]:
                clean = _sanitize_translation_line(translation)
                if clean:
                    lines.append(clean)
                    lines.append("")
        else:
            lines.append("[Nenhum texto nesta pagina]")
            lines.append("")

    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def determine_output_path(input_path: str, output_arg: str | None) -> Path:
    """Determina o caminho de saída."""
    path = Path(input_path)
    base_name = path.stem.replace("_corrigido", "").replace("_raw", "")
    
    if output_arg:
        out = Path(output_arg)
        if out.suffix.lower() == ".txt":
            return out
        else:
            out.mkdir(parents=True, exist_ok=True)
            return out / f"{base_name}_traduzido.txt"

    # Padrão: salva ao lado do arquivo de entrada em uma pasta 'output_ptbr'
    default_dir = path.parent / "output_ptbr"
    default_dir.mkdir(parents=True, exist_ok=True)
    
    return default_dir / f"{base_name}_traduzido.txt"


def print_banner():
    """Exibe banner."""
    banner = """
╔══════════════════════════════════════════╗
║     🌐 Manga Translator (EN→PT-BR)      ║
║      Tradução local via Ollama           ║
╚══════════════════════════════════════════╝
    """
    print(banner)


def print_summary(
    total_pages: int,
    total_balloons: int,
    elapsed: float,
    output_path: Path,
    model: str,
):
    """Exibe resumo."""
    print()
    print("─" * 50)
    print("📊 RESUMO")
    print("─" * 50)
    print(f"  📄 Paginas processadas:  {total_pages}")
    print(f"  💬 Baloes traduzidos:    {total_balloons}")
    print(f"  🤖 Modelo:               {model}")
    print(f"  ⏱️  Tempo total:          {elapsed:.1f}s")
    print(f"  📁 Arquivo de saida:     {output_path}")
    print("─" * 50)
    print()
    print("✅ Traducao concluida!")
    print()


def main():
    parser = create_parser()
    args = parser.parse_args()

    print_banner()

    # Verifica arquivo de entrada
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"❌ Arquivo nao encontrado: {args.input}")
        sys.exit(1)

    # Verifica Ollama
    print("🔌 Verificando conexao com Ollama...")
    if not check_ollama_running():
        print("❌ Ollama nao esta rodando!")
        print("   Inicie o Ollama e tente novamente.")
        print("   No Windows, o Ollama geralmente inicia automaticamente.")
        sys.exit(1)
    print("   Conectado!")

    # Verifica modelo
    print(f"🤖 Verificando modelo: {args.model}")
    if not check_model_available(args.model):
        print(f"   Modelo '{args.model}' nao encontrado. Baixando...")
        print(f"   Execute: ollama pull {args.model}")
        print(f"   E tente novamente.")
        sys.exit(1)
    print("   Modelo disponivel!")
    print()

    # Lê arquivo do OCR
    print(f"📂 Lendo arquivo: {input_path}")
    pages = parse_ocr_file(input_path)
    total_balloons = sum(len(p["texts"]) for p in pages)
    print(f"   {len(pages)} pagina(s), {total_balloons} balao(oes)")
    print()

    # Carrega referência OCR Raw original para Dupla Alimentação (estilo e gírias originais)
    raw_pages_map = {}
    try:
        raw_input_path = input_path.parent / input_path.name.replace("_corrigido.txt", "_raw.txt")
        if raw_input_path.exists() and raw_input_path != input_path:
            for p in parse_ocr_file(raw_input_path):
                raw_pages_map[p["header"]] = p["texts"]
            print(f"🔗 Referência OCR Raw original carregada ({len(raw_pages_map)} páginas) para Dupla Alimentação.")
            print()
    except Exception:
        pass

    # Determina saída
    output_path = determine_output_path(args.input, args.output)

    # Cache inteligente de Auto-Mesclagem: se o arquivo traduzido já existe, carrega páginas já prontas
    existing_translations_map = {}
    if not args.force and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8-sig") as _f:
                _raw = _f.read()
            # Extrai pares [EN]/[BR] válidos por página do arquivo bilíngue
            import re as _re
            _page_blocks = _re.split(r'={10,}\n(PÁGINA[^\n]+)\n={10,}', _raw)
            for i in range(1, len(_page_blocks), 2):
                _header = _page_blocks[i].strip()
                _body = _page_blocks[i + 1] if i + 1 < len(_page_blocks) else ""
                _en_lines = _re.findall(r'\[EN\]:\s*(.+)', _body)
                _br_lines = _re.findall(r'\[BR\]:\s*(.+)', _body)
                # Só considera página como traduzida se tiver ao menos 1 [BR] com conteúdo real
                _valid_brs = [br.strip() for br in _br_lines if br.strip() and not br.strip().upper().startswith("[EN]")]
                if _valid_brs and len(_valid_brs) == len(_en_lines):
                    _pairs = [f"[EN]: {en.strip()}\n[BR]: {br}" for en, br in zip(_en_lines, _valid_brs)]
                    existing_translations_map[_header] = _pairs
            if existing_translations_map:
                print(f"⚡ {len(existing_translations_map)} página(s) já traduzida(s) encontradas em cache. Mantendo intactas sem reprocessar!")
                print()
        except Exception:
            pass

    # Traduz
    print(f"🔄 Traduzindo com {args.model}...")
    if args.context:
        print(f"   Contexto: {args.context}")
    print()

    # Carrega dicionários
    dict_content = ""
    if args.dict_global and Path(args.dict_global).exists():
        with open(args.dict_global, "r", encoding="utf-8") as f:
            dict_content += f.read() + "\n"
    if args.dict_local and Path(args.dict_local).exists():
        with open(args.dict_local, "r", encoding="utf-8") as f:
            dict_content += f.read() + "\n"

    if dict_content.strip():
        print("📖 Dicionários carregados e aplicados.")

    start_time = time.time()
    balloon_count = 0
    prev_page_context = ""

    for page_idx, page in enumerate(pages):
        page["translations"] = []
        
        # Ignora páginas sem texto
        if not page.get("texts") or (len(page["texts"]) == 1 and "[Nenhum texto" in page["texts"][0]):
            page["translations"] = page.get("texts", [])
            continue
            
        # Se a página já existe traduzida no arquivo anterior, aproveita o cache
        if page.get("header") in existing_translations_map:
            print(f"⏭️ [Página {page_idx + 1}/{len(pages)}] {page.get('header')}: Já traduzida em cache! Mantendo intacta.")
            page["translations"] = existing_translations_map[page["header"]]
            continue

        # Ignora páginas que já foram traduzidas (contêm tag [BR]:)
        is_translated = any(t.strip().upper().startswith("[BR]:") for t in page["texts"])
        if is_translated:
            page["translations"] = page["texts"]
            continue
            
        page_texts = page["texts"]
        page_context = page.get("context", "")
        raw_texts = raw_pages_map.get(page["header"], None)
        
        print(f"    [Página {page_idx + 1}/{len(pages)}] Traduzindo {len(page_texts)} balõe(s)...", end="\n", flush=True)
        
        translations = translate_texts(
            texts=page_texts,
            model=args.model,
            context=args.context,
            dict_content=dict_content,
            temperature=args.temperature,
            tone=args.tone,
            rag_workspace=Path(args.rag_workspace) if args.rag_workspace else None,
            page_context=page_context,
            raw_texts=raw_texts,
            prev_page_context=prev_page_context,
        )
        
        if args.verbose:
            for text, tr in zip(page_texts, translations):
                print(f"      EN: {text}")
                print(f"      BR: {tr}")
        else:
            if translations:
                preview = translations[-1][:60] + "..." if len(translations[-1]) > 60 else translations[-1]
                print(f"    [Página {page_idx + 1}/{len(pages)}] -> {preview}")
        
        valid_translations = []
        for text, translation in zip(page_texts, translations):
            if translation.strip().upper() == "[IGNORE]":
                continue
                
            balloon_count += 1
            valid_translations.append(translation.strip())
            if args.bilingual:
                page["translations"].append(f"[EN]: {text}\n[BR]: {translation}")
            else:
                page["translations"].append(translation)
                
        if valid_translations:
            prev_page_context = "\n".join(valid_translations[-3:])

    elapsed = time.time() - start_time

    # Libera a memória da placa de vídeo (descarrega o modelo do Ollama)
    print("  🧹 Liberando a memória da placa de vídeo (descarregando Ollama)...")
    try:
        requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={"model": args.model, "keep_alive": 0},
            timeout=5
        )
    except Exception:
        pass

    # Gera arquivo traduzido
    generate_translated_output(pages, output_path)

    # Resumo
    print_summary(len(pages), balloon_count, elapsed, output_path, args.model)


if __name__ == "__main__":
    main()
