#!/usr/bin/env python3
"""
Manga OCR Extractor
===================
Extrai texto em inglês de páginas de mangá/comics usando OCR local (EasyOCR).
Gera um arquivo .txt organizado por página, pronto para tradução.

Uso:
    python manga_ocr.py ./capitulo-01/
    python manga_ocr.py pagina.png -o texto_extraido.txt
    python manga_ocr.py ./capitulo-01/ --reading-order comic --confidence 0.4
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Força encoding UTF-8 no Windows para suportar emojis no console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np

# Formatos de imagem suportados
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def create_parser() -> argparse.ArgumentParser:
    """Cria e retorna o parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog="manga_ocr",
        description="Extrai texto de páginas de mangá/comics via OCR local.",
        epilog="Exemplo: python manga_ocr.py ./capitulo-01/ -o capitulo01.txt --gpu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input",
        type=str,
        help="Caminho para uma imagem ou pasta com imagens de mangá.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Caminho do arquivo .txt de saída. Padrão: ./output/<nome_da_pasta>.txt",
    )
    parser.add_argument(
        "-c",
        "--confidence",
        type=float,
        default=0.55,
        help="Confiança mínima para aceitar uma detecção (0.0 a 1.0). Padrão: 0.55",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Desativa pré-processamento de imagem (escala de cinza + contraste).",
    )
    parser.add_argument(
        "--reading-order",
        choices=["manga", "comic"],
        default="manga",
        help="Ordem de leitura: 'manga' (direita->esquerda) ou 'comic' (esquerda->direita). Padrao: manga",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Ativa uso de GPU (requer NVIDIA CUDA). Recomendado com sua RTX 2060 Super!",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostra informações detalhadas durante o processamento.",
    )

    return parser


def collect_images(input_path: str) -> list[Path]:
    """
    Coleta imagens a partir do caminho fornecido.
    Retorna lista de paths ordenada naturalmente (pag1, pag2, ... pag10).
    """
    path = Path(input_path)

    if path.is_file():
        if path.suffix.lower() in SUPPORTED_FORMATS:
            return [path]
        else:
            print(f"❌ Formato não suportado: {path.suffix}")
            print(f"   Formatos aceitos: {', '.join(sorted(SUPPORTED_FORMATS))}")
            sys.exit(1)

    elif path.is_dir():
        images = [
            f
            for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
        ]
        if not images:
            print(f"❌ Nenhuma imagem encontrada em: {path}")
            print(f"   Formatos aceitos: {', '.join(sorted(SUPPORTED_FORMATS))}")
            sys.exit(1)

        # Ordenação natural: pag1, pag2, ..., pag10 (não pag1, pag10, pag2)
        import re
        def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
            return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s.name)]
        return sorted(images, key=natural_sort_key)

    else:
        print(f"❌ Caminho não encontrado: {input_path}")
        sys.exit(1)


def deskew_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
    
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Identifica linhas tortas entre -15 e 15 graus (ignora perfeitas)
            if -15 < angle < 15 and abs(angle) > 0.5:
                angles.append(angle)
            elif 75 < angle < 105:
                angles.append(angle - 90)
            elif -105 < angle < -75:
                angles.append(angle + 90)
                
        if angles:
            median_angle = np.median(angles)
            if abs(median_angle) > 0.5:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated
    return image


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Pré-processa a imagem para a V2:
    1. Deskew Automático
    2. Isolamento Matemático de Balões
    3. CLAHE (Contraste) e Denoising
    """
    # 1. Deskew
    deskewed = deskew_image(image)
    
    # 2. Grayscale
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY) if len(deskewed.shape) == 3 else deskewed.copy()
    
    # 3. CLAHE (Melhorar contraste local sem destruir fundo escuro)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 4. Suave Denoising
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10, templateWindowSize=7, searchWindowSize=21)
    
    return denoised


def cluster_text_blocks(results: list, image_height: int, image_width: int) -> list[list]:
    """
    Agrupa detecções próximas em clusters (simulando balões de fala).
    
    Usa distância entre centros dos bounding boxes para decidir se duas
    detecções pertencem ao mesmo balão. O threshold é proporcional ao
    tamanho da imagem para funcionar com diferentes resoluções.
    """
    if not results:
        return []

    # Prepara blocos com metadados de posição
    blocks = []
    for detection in results:
        bbox, text, confidence = detection
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)
        min_y = min(ys)
        max_y = max(ys)
        min_x = min(xs)
        max_x = max(xs)
        block_height = max_y - min_y
        blocks.append({
            "bbox": bbox,
            "text": text,
            "confidence": confidence,
            "center_x": center_x,
            "center_y": center_y,
            "min_y": min_y,
            "max_y": max_y,
            "min_x": min_x,
            "max_x": max_x,
            "height": block_height,
            "cluster": -1,
        })

    # Threshold de distância para agrupar: baseado na altura média dos blocos
    # Blocos que estão a menos de 2x a altura média de distância vertical
    # são considerados do mesmo balão
    avg_height = sum(b["height"] for b in blocks) / len(blocks) if blocks else 50
    # Gap máximo entre bordas dos bounding boxes (não centros!)
    # Thresholds mais rigorosos para evitar mesclar balões separados
    vertical_gap_threshold = max(avg_height * 1.0, 30)
    horizontal_gap_threshold = max(avg_height * 1.2, 35)

    # Clustering por proximidade de bordas (union-find simplificado)
    cluster_id = 0
    for i, block in enumerate(blocks):
        if block["cluster"] != -1:
            continue
        
        # Novo cluster
        block["cluster"] = cluster_id
        queue = [i]
        
        while queue:
            current_idx = queue.pop(0)
            current = blocks[current_idx]
            
            for j, other in enumerate(blocks):
                if other["cluster"] != -1:
                    continue
                
                # Calcula gap entre bordas dos bounding boxes
                # Gap vertical: distância entre a borda inferior de um e superior do outro
                if current["max_y"] < other["min_y"]:
                    vert_gap = other["min_y"] - current["max_y"]
                elif other["max_y"] < current["min_y"]:
                    vert_gap = current["min_y"] - other["max_y"]
                else:
                    vert_gap = 0  # Se sobrepõem verticalmente

                # Gap horizontal: distância entre bordas horizontais
                if current["max_x"] < other["min_x"]:
                    horiz_gap = other["min_x"] - current["max_x"]
                elif other["max_x"] < current["min_x"]:
                    horiz_gap = current["min_x"] - other["max_x"]
                else:
                    horiz_gap = 0  # Se sobrepõem horizontalmente
                
                # Calcula a sobreposição horizontal real (em pixels) entre os dois blocos
                overlap_start = max(current["min_x"], other["min_x"])
                overlap_end = min(current["max_x"], other["max_x"])
                overlap_width = max(0, overlap_end - overlap_start)
                
                # Largura do bloco mais estreito (referência para o ratio)
                current_width = current["max_x"] - current["min_x"]
                other_width = other["max_x"] - other["min_x"]
                min_width = min(current_width, other_width) if min(current_width, other_width) > 0 else 1
                overlap_ratio = overlap_width / min_width

                # Lógica Inteligente para identificar formato do Balão (Blocos de texto)
                # 1. Mesma Linha: O limite horizontal é o tamanho de 1 caractere de espaço (máximo 10 pixels)
                is_same_line = (vert_gap == 0) and (horiz_gap <= 10)
                
                # 2. Linhas Empilhadas (Balão): Precisam ter pelo menos 70% de sobreposição horizontal
                #    E a distância vertical não pode exceder 0.8x a altura média (apenas linhas bem próximas)
                is_stacked = (overlap_ratio >= 0.70) and (vert_gap < max(avg_height * 0.8, 20)) and (horiz_gap == 0)
                
                # 3. Pequeno deslocamento (texto diagonal ou itálico leve)
                is_diagonal = (horiz_gap < 10) and (vert_gap < 10)

                if is_same_line or is_stacked or is_diagonal:
                    other["cluster"] = cluster_id
                    queue.append(j)
        
        cluster_id += 1

    # Agrupa blocos por cluster
    clusters = {}
    for block in blocks:
        cid = block["cluster"]
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(block)

    return list(clusters.values())


def sort_and_merge_clusters(
    clusters: list[list],
    reading_order: str = "manga",
) -> list[str]:
    """
    Ordena os clusters na ordem de leitura e junta o texto dentro de cada um.
    
    Para mangá: clusters ordenados de cima para baixo, direita para esquerda.
    Para comic: clusters ordenados de cima para baixo, esquerda para direita.
    
    Dentro de cada cluster, o texto é ordenado de cima para baixo.
    """
    if not clusters:
        return []

    # Calcula centro de cada cluster
    cluster_info = []
    for cluster in clusters:
        avg_x = sum(b["center_x"] for b in cluster) / len(cluster)
        avg_y = sum(b["min_y"] for b in cluster) / len(cluster)
        cluster_info.append({
            "blocks": cluster,
            "avg_x": avg_x,
            "avg_y": avg_y,
        })

    # Agrupa clusters em faixas horizontais (painéis)
    cluster_info.sort(key=lambda c: c["avg_y"])
    
    rows = []
    current_row = [cluster_info[0]]
    # Threshold para agrupar as faixas horizontais de painéis do mangá (Cima/Meio/Baixo)
    row_threshold = 80

    for ci in cluster_info[1:]:
        if abs(ci["avg_y"] - current_row[0]["avg_y"]) < row_threshold:
            current_row.append(ci)
        else:
            rows.append(current_row)
            current_row = [ci]
    rows.append(current_row)

    # Ordena clusters dentro de cada faixa por X
    sorted_texts = []
    for row in rows:
        if reading_order == "manga":
            row_sorted = sorted(row, key=lambda c: c["avg_x"], reverse=True)
        else:
            row_sorted = sorted(row, key=lambda c: c["avg_x"])

        for cluster in row_sorted:
            # Dentro do cluster, ordena blocos de cima para baixo
            blocks_sorted = sorted(cluster["blocks"], key=lambda b: b["min_y"])
            
            # Junta texto do cluster, tratando hífens no final da linha
            merged = ""
            lines = [b["text"].strip() for b in blocks_sorted]
            for i, line in enumerate(lines):
                if line.endswith("-") and i < len(lines) - 1:
                    merged += line[:-1] # Remove hífen e não adiciona espaço
                else:
                    merged += line + (" " if i < len(lines) - 1 else "")
                    
            sorted_texts.append(merged.strip())

    return sorted_texts


def process_image(
    image_path: Path,
    reader,
    confidence_threshold: float,
    reading_order: str,
    preprocess: bool,
    verbose: bool,
) -> list[str]:
    """
    Processa uma única imagem e retorna lista de textos extraídos.
    """
    # Carrega imagem usando numpy para suportar caminhos Unicode no Windows
    image_array = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    if image is None:
        print(f"  ⚠️  Não foi possível carregar: {image_path.name}")
        return []

    # Pré-processamento opcional
    if preprocess:
        processed = preprocess_image(image)
    else:
        processed = image

    # OCR - Parâmetros agressivos para maximizar qualidade
    # mag_ratio=2.0 e adjust_contrast melhoram detecção de fontes pequenas
    results = reader.readtext(
        processed,
        paragraph=False,
        width_ths=0.5,
        mag_ratio=2.0,
        contrast_ths=0.1,
        adjust_contrast=0.5
    )

    if verbose:
        print(f"  🔍 {len(results)} detecções brutas")

    # Filtros Avançados de Ruído
    filtered = []
    import re
    for bbox, text, conf in results:
        if conf < confidence_threshold:
            continue
            
        # 1. Filtro Físico: Ignora caixas absurdamente pequenas (poeira, screentones, bordas)
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        
        # Em mangás de qualidade média/alta, letras têm pelo menos ~12px de altura
        if height < 12 or width < 8:
            continue
            
        # 2. Filtro Semântico: Ignora "alucinações" do OCR compostas de lixo
        t = text.strip()
        if not t:
            continue
            
        # Se tem pelo menos uma letra ou número, é considerado válido
        has_alnum = re.search(r'[a-zA-Z0-9]', t)
        
        # Se NÃO tem letra/número, só salvamos se for uma pontuação clássica isolada (ex: "!!", "?", "...")
        # Lixo comum do EasyOCR: "}_", "||", "\\/", "][", etc.
        is_valid_punctuation = re.fullmatch(r'[!?.\-,~…"\']+', t)
        
        # 3. Filtro Anti-Onomatopeia e Speedlines (Opcional, mas forte para mangás)
        # Remove lixo como "SWSH", "TMP", "WCH", "FS @VER", etc.
        words = t.split()
        if len(words) <= 3:
            # Se a string inteira não tiver nenhuma vogal e tiver letras, é quase certeza que é speedline/SFX (ex: SWSH, TMP, WCH)
            alpha_only = re.sub(r'[^a-zA-Z]', '', t).lower()
            if alpha_only and not re.search(r'[aeiouy]', alpha_only):
                continue
                
            # Lista de onomatopeias muito comuns
            sfx_blacklist = {'boom', 'bam', 'wham', 'thud', 'grab', 'swish', 'fwoosh', 'whoosh', 'whack', 'thrash', 'slide', 'whiff', 'whirl', 'sigh', 'gasp', 'pant'}
            if alpha_only in sfx_blacklist:
                continue

        filtered.append((bbox, text, conf))

    if verbose:
        removed = len(results) - len(filtered)
        if removed > 0:
            print(f"  🗑️  {removed} detecções removidas (confiança < {confidence_threshold})")

    # Agrupa detecções próximas em clusters (balões de fala)
    img_h, img_w = image.shape[:2]
    clusters = cluster_text_blocks(filtered, img_h, img_w)

    if verbose:
        print(f"  💬 {len(clusters)} balão(ões) detectado(s)")

    # Ordena clusters na ordem de leitura e junta texto
    texts = sort_and_merge_clusters(clusters, reading_order)

    return texts


def generate_output(
    pages: list[dict],
    output_path: Path,
) -> None:
    """
    Gera o arquivo .txt de saída com o texto extraído.
    
    Formato:
    ========================================
    PÁGINA 1: nome_do_arquivo.png
    ========================================
    
    Texto extraído...
    """
    # Cria diretório de saída se necessário
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for page in pages:
        separator = "=" * 50
        lines.append(separator)
        lines.append(f"PÁGINA {page['number']}: {page['filename']}")
        lines.append(separator)
        lines.append("")

        if page["texts"]:
            for text in page["texts"]:
                lines.append(text)
                lines.append("")
        else:
            lines.append("[Nenhum texto detectado nesta página]")
            lines.append("")

    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write(content)


def determine_output_path(input_path: str, output_arg: str | None) -> Path:
    """Determina o caminho de saída do arquivo .txt."""
    path = Path(input_path)
    base_name = path.name if path.is_dir() else path.stem
    
    if output_arg:
        out = Path(output_arg)
        if out.suffix.lower() == ".txt":
            return out
        else:
            out.mkdir(parents=True, exist_ok=True)
            return out / f"{base_name}_raw.txt"

    output_dir = path.parent / "output_raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{base_name}_raw.txt"


def print_banner():
    """Exibe banner do programa."""
    banner = """
╔══════════════════════════════════════════╗
║       📖 Manga OCR Extractor 📖         ║
║    Extração de texto para tradução       ║
╚══════════════════════════════════════════╝
    """
    print(banner)


def print_summary(total_pages: int, total_texts: int, elapsed: float, output_path: Path):
    """Exibe resumo do processamento."""
    print()
    print("─" * 50)
    print("📊 RESUMO")
    print("─" * 50)
    print(f"  📄 Páginas processadas:  {total_pages}")
    print(f"  💬 Textos extraídos:     {total_texts}")
    print(f"  ⏱️  Tempo total:          {elapsed:.1f}s")
    print(f"  📁 Arquivo de saída:     {output_path}")
    print("─" * 50)
    print()
    print("✅ Pronto! O texto está pronto para ser traduzido.")
    print()


def main():
    parser = create_parser()
    args = parser.parse_args()

    print_banner()

    # Coleta imagens
    print(f"📂 Buscando imagens em: {args.input}")
    images = collect_images(args.input)
    print(f"   Encontradas: {len(images)} imagem(ns)")
    print()

    # Determina saída
    output_path = determine_output_path(args.input, args.output)

    # Inicializa EasyOCR
    print("🚀 Inicializando EasyOCR...")
    gpu_status = "GPU (CUDA)" if args.gpu else "CPU"
    print(f"   Dispositivo: {gpu_status}")
    print(f"   Idioma: Inglês (en)")
    print()

    try:
        import easyocr
        reader = easyocr.Reader(
            ["en"],
            gpu=args.gpu,
            verbose=False,
        )
    except Exception as e:
        print(f"❌ Erro ao inicializar EasyOCR: {e}")
        if args.gpu:
            print("   💡 Tente rodar sem --gpu, ou verifique se CUDA está instalado.")
        sys.exit(1)

    # Processa cada imagem
    print(f"🔄 Processando {len(images)} página(s)...")
    print(f"   Ordem de leitura: {'Manga (direita->esquerda)' if args.reading_order == 'manga' else 'Comic (esquerda->direita)'}")
    print(f"   Pré-processamento: {'Ativado' if not args.no_preprocess else 'Desativado'}")
    print(f"   Confiança mínima: {args.confidence}")
    print()

    pages = []
    total_texts = 0
    start_time = time.time()

    for i, image_path in enumerate(images, 1):
        print(f"  [{i}/{len(images)}] 📄 {image_path.name}", end="")

        page_start = time.time()
        texts = process_image(
            image_path=image_path,
            reader=reader,
            confidence_threshold=args.confidence,
            reading_order=args.reading_order,
            preprocess=not args.no_preprocess,
            verbose=args.verbose,
        )
        page_elapsed = time.time() - page_start

        pages.append({
            "number": i,
            "filename": image_path.name,
            "texts": texts,
        })

        total_texts += len(texts)
        print(f"  ->  {len(texts)} texto(s)  ({page_elapsed:.1f}s)")

    elapsed = time.time() - start_time

    # Gera arquivo de saída
    generate_output(pages, output_path)

    # Resumo
    print_summary(len(pages), total_texts, elapsed, output_path)


if __name__ == "__main__":
    main()
