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

TRANSLATION_PROMPT = """Você é um tradutor profissional de mangás. Traduza os seguintes textos de INGLÊS para PORTUGUÊS BRASILEIRO.
Os textos fornecidos são balões de fala extraídos de uma página de mangá. Cada linha numerada [1], [2], etc., representa um balão separado.

Regras OBRIGATÓRIAS:
- Mantenha o tom {tone}
- Preserve nomes próprios SEM traduzir (ex: Harry, Daniel, Zara)
- Mantenha interjeições e onomatopeias quando apropriado (ex: "Tch!", "Hah!")
- Se houver erros de OCR óbvios, corrija-os na tradução (ex: "YO4" -> "Você", "CONTINLE" -> "continuar")
- Retorne APENAS as traduções, com a MESMA numeração de entrada (ex: [1] Texto traduzido, [2] Outro texto)
- Não adicione explicações, comentários ou aspas extras.
- Se uma frase original for um trocadilho, tiver duplo sentido ou for altamente ambígua, forneça a sua tradução principal e adicione uma nota logo abaixo (na mesma linha ou na próxima, sem quebrar o formato) no formato `[Alt: <outra possível interpretação>]`. NÃO use a tag [Alt:] para frases óbvias.
- Você DEVE retornar EXATAMENTE o mesmo número de itens/linhas que a entrada.

{dict_section}

{context_section}TEXTOS PARA TRADUZIR:
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
        default="gemma3:4b",
        help="Modelo Ollama para traducao. Padrao: gemma3:4b",
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


def translate_texts(
    texts: list[str],
    model: str,
    context: str | None = None,
    dict_content: str = "",
    temperature: float = 0.3,
    tone: str = "casual e natural",
    rag_workspace: Path | None = None,
) -> list[str]:
    """Traduz uma lista de textos em lote usando o Ollama."""
    if not texts:
        return []

    context_section = ""
    if context:
        context_section += f"Contexto da obra: {context}\n\n"
        
    if rag_workspace:
        try:
            import sys
            if str(rag_workspace) not in sys.path:
                sys.path.append(str(rag_workspace))
            import rag_memory
            
            rag_hits = []
            for i, text in enumerate(texts):
                match_br = rag_memory.query_memory(rag_workspace, text, threshold=0.3) # Alta precisão
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

    # Numera os textos para envio em lote
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
        },
    }

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
        translated = list(texts) # Inicializa com os originais como fallback
        import re
        for match in re.finditer(r'\[(\d+)\]\s*(.*?)(?=\[\d+\]|$)', raw_output, re.DOTALL):
            idx = int(match.group(1)) - 1
            translation = match.group(2).strip()
            if 0 <= idx < len(translated):
                translated[idx] = translation
                
        return translated
    except requests.ConnectionError:
        print("  ❌ Erro: Ollama nao esta rodando. Inicie com 'ollama serve'.")
        sys.exit(1)
    except requests.Timeout:
        return ["[ERRO: Timeout na traducao]"] * len(texts)
    except Exception as e:
        return [f"[ERRO: {e}]"] * len(texts)


def parse_ocr_file(file_path: Path) -> list[dict]:
    """
    Lê o arquivo .txt do OCR e extrai as páginas e textos.
    
    Retorna lista de dicts:
    [{"header": "PÁGINA 1: 017.jpg", "texts": ["texto1", "texto2"]}, ...]
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

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
            current_page = {"header": line, "texts": []}
            continue

        # Texto do balão
        if current_page is not None and line.strip():
            current_page["texts"].append(line.strip())

    # Última página
    if current_page is not None:
        pages.append(current_page)

    return pages


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
                lines.append(translation)
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

    # Determina saída
    output_path = determine_output_path(args.input, args.output)

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
        print("📖 Dicionarios carregados e aplicados.")

    start_time = time.time()
    balloon_count = 0

    # Extrai textos globalmente mantendo mapeamento
    global_texts = []
    mapping = [] # (page_idx)
    
    for page_idx, page in enumerate(pages):
        page["translations"] = []
        for text in page.get("texts", []):
            global_texts.append(text)
            mapping.append(page_idx)
            
    if not global_texts:
        print("  ❌ Nenhum texto detectado nas páginas.")
        generate_translated_output(pages, output_path)
        print_summary(len(pages), 0, time.time() - start_time, output_path, args.model)
        return

    BATCH_SIZE = 50
    chunks = [global_texts[i:i + BATCH_SIZE] for i in range(0, len(global_texts), BATCH_SIZE)]
    
    print(f"  📦 Total de {len(global_texts)} balão(ões) extraídos.")
    print(f"  📦 Divididos em {len(chunks)} lote(s) global(is) de no máximo {BATCH_SIZE} balões cada.")
    print()

    global_translations = []
    
    for chunk_idx, chunk in enumerate(chunks):
        print(f"    [Lote {chunk_idx + 1}/{len(chunks)}] Traduzindo {len(chunk)} balõe(s)...", end="", flush=True)
        t_start = time.time()
        
        translations = translate_texts(
            texts=chunk,
            model=args.model,
            context=args.context,
            dict_content=dict_content,
            temperature=args.temperature,
            tone=args.tone,
            rag_workspace=Path(args.rag_workspace) if args.rag_workspace else None,
        )
        
        t_elapsed = time.time() - t_start
        
        global_translations.extend(translations)
        
        if args.verbose:
            for text, tr in zip(chunk, translations):
                print(f"      EN: {text}")
                print(f"      BR: {tr}")
        else:
            # Mostra preview apenas do último do chunk
            if translations:
                preview = translations[-1][:60] + "..." if len(translations[-1]) > 60 else translations[-1]
                print(f"      -> {preview}")
        print()

    # Reagrupa os resultados nas páginas
    for text, translation, page_idx in zip(global_texts, global_translations, mapping):
        page = pages[page_idx]
        balloon_count += 1
        
        if args.bilingual:
            page["translations"].append(f"[EN]: {text}\n[BR]: {translation}")
        else:
            page["translations"].append(translation)

    elapsed = time.time() - start_time

    # Gera arquivo traduzido
    generate_translated_output(pages, output_path)

    # Resumo
    print_summary(len(pages), balloon_count, elapsed, output_path, args.model)


if __name__ == "__main__":
    main()
