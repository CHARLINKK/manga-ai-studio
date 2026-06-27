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

import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"

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
        "--append",
        action="store_true",
        help="Anexa os resultados a um arquivo .txt existente em vez de sobrescrever.",
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
                    
            merged = merged.strip()
            
            # Filtro de ruído visual extremo
            merged_upper = merged.upper()
            
            # 1. Ignorar strings indesejadas exatas (marcas d'água ou alucinações comuns)
            denylist = ['2MB', '1MB', '3MB', '4MB', '5MB', '000', 'OOO']
            if merged_upper in denylist:
                continue
                
            # 2. Se for 1 único caractere que não faz sentido sozinho em inglês, ignora
            if len(merged) == 1 and merged_upper not in ['I', 'A', 'O', '?', '!']:
                continue
                
            # 3. Se for muito curto e não tiver letras nem pontuação importante, ignora (ex: '1', '0', '..')
            if len(merged) <= 2 and not any(c.isalpha() for c in merged):
                if not any(c in '?!' for c in merged):
                    continue
                    
            if merged:
                sorted_texts.append(merged)

    return sorted_texts


def process_image(
    image_path: Path,
    model,
    processor,
    device: str,
    torch_dtype,
    reading_order: str,
    verbose: bool,
) -> tuple[list[str], str]:
    """
    Processa uma única imagem e retorna (lista_de_textos, descricao_da_cena).
    """
    from PIL import Image
    
    try:
        # Abre a imagem com PIL
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"  ⚠️  Não foi possível carregar: {image_path.name}")
        return []

    # Prompt para Florence-2
    task_prompt = "<OCR_WITH_REGION>"
    
    # Slicing: Corta a imagem em 3 partes horizontais (Topo, Meio, Base) para triplicar a resolução
    w, h = image.size
    overlap = int(h * 0.05) # 5% de sobreposição
    
    slice_height = h // 3
    
    top_img = image.crop((0, 0, w, slice_height + overlap))
    mid_img = image.crop((0, slice_height - overlap, w, (slice_height * 2) + overlap))
    bottom_img = image.crop((0, (slice_height * 2) - overlap, w, h))
    
    all_quad_boxes = []
    all_labels = []
    
    slices = [
        (top_img, 0),
        (mid_img, slice_height - overlap),
        (bottom_img, (slice_height * 2) - overlap)
    ]
    
    for idx, (slice_img, y_offset) in enumerate(slices):
        inputs = processor(text=task_prompt, images=slice_img, return_tensors="pt").to(device, torch_dtype)
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
            do_sample=False
        )
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(generated_text, task=task_prompt, image_size=(slice_img.width, slice_img.height))
        
        ocr_results = parsed_answer.get(task_prompt, {})
        quad_boxes = ocr_results.get("quad_boxes", [])
        labels = ocr_results.get("labels", [])
        
        for box, label in zip(quad_boxes, labels):
            adjusted_box = [
                box[0], box[1] + y_offset,
                box[2], box[3] + y_offset,
                box[4], box[5] + y_offset,
                box[6], box[7] + y_offset
            ]
            
            center_y = (adjusted_box[1] + adjusted_box[5]) / 2
            
            # Remove duplicatas nas áreas de sobreposição verificando em qual terço o centro Y está
            if idx == 0 and center_y > slice_height:
                continue
            if idx == 1 and (center_y <= slice_height or center_y > slice_height * 2):
                continue
            if idx == 2 and center_y <= slice_height * 2:
                continue
                
            all_quad_boxes.append(adjusted_box)
            all_labels.append(label)
            
    quad_boxes = all_quad_boxes
    labels = all_labels
    
    if verbose:
        print(f"  🔍 {len(labels)} detecções brutas encontradas.")
    
    filtered = []
    import re
    
    # O confidence não é retornado pelo Florence nativamente, usaremos 1.0 como dummy
    for i in range(len(labels)):
        text = labels[i]
        box = quad_boxes[i] # [x1, y1, x2, y2, x3, y3, x4, y4]
        
        # Converte para o formato esperado pelo cluster_text_blocks: [[x,y], [x,y], [x,y], [x,y]]
        bbox = [
            [box[0], box[1]],
            [box[2], box[3]],
            [box[4], box[5]],
            [box[6], box[7]]
        ]
        
        # Filtros Semânticos e Físicos
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        
        if height < 10 or width < 6:
            continue
            
        t = text.strip()
        if not t:
            continue
            
        # Pula onomatopeias óbvias se quiser, Florence é bom em ler sons de impacto
        has_alnum = re.search(r'[a-zA-Z0-9]', t)
        if not has_alnum and not re.fullmatch(r'[!?.\-,~…"\']+', t):
            continue
            
        filtered.append((bbox, t, 1.0))


    if verbose:
        removed = len(labels) - len(filtered)
        if removed > 0:
            print(f"  🗑️  {removed} detecções removidas (tamanho mínimo ou lixo)")

    # Agrupa detecções próximas em clusters (balões de fala)
    img_h, img_w = image.height, image.width
    clusters = cluster_text_blocks(filtered, img_h, img_w)

    if verbose:
        print(f"  💬 {len(clusters)} balão(ões) detectado(s). Iniciando Fase 2 (Sniper OCR)...")

    # Fase 2: Sniper OCR (Two-Pass Zoom)
    # Recorta a imagem em volta de cada balão detectado para dar um zoom extremo no Florence-2
    sniper_task_prompt = "<OCR>"
    sniper_clusters = []
    
    for cluster in clusters:
        # Pega a bounding box do cluster inteiro (cada item é um dict)
        min_x = min(p[0] for item in cluster for p in item["bbox"])
        min_y = min(p[1] for item in cluster for p in item["bbox"])
        max_x = max(p[0] for item in cluster for p in item["bbox"])
        max_y = max(p[1] for item in cluster for p in item["bbox"])
        
        # Adiciona uma margem de segurança (padding) dinâmica
        # Para textos muito pequenos, 15px é muita coisa e captura lixo ao redor.
        # Usa 10% do tamanho, com mínimo de 5px e máximo de 15px.
        bw = max_x - min_x
        bh = max_y - min_y
        pad = max(5, min(15, int(min(bw, bh) * 0.15)))
        
        crop_x1 = max(0, min_x - pad)
        crop_y1 = max(0, min_y - pad)
        crop_x2 = min(img_w, max_x + pad)
        crop_y2 = min(img_h, max_y + pad)
        
        if (crop_x2 - crop_x1) < 10 or (crop_y2 - crop_y1) < 10:
            sniper_clusters.append(cluster)
            continue
            
        cropped_img = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        # Roda o Florence-2 na imagem minúscula (agora redimensionada para gigante internamente)
        c_inputs = processor(text=sniper_task_prompt, images=cropped_img, return_tensors="pt").to(device, torch_dtype)
        c_generated_ids = model.generate(
            input_ids=c_inputs["input_ids"],
            pixel_values=c_inputs["pixel_values"],
            max_new_tokens=512,
            num_beams=3,
            do_sample=False
        )
        c_generated_text = processor.batch_decode(c_generated_ids, skip_special_tokens=False)[0]
        c_parsed_answer = processor.post_process_generation(c_generated_text, task=sniper_task_prompt, image_size=(cropped_img.width, cropped_img.height))
        
        sniper_text = c_parsed_answer.get(sniper_task_prompt, "").replace("\n", " ")
        import re
        
        # 1. Trata hífens: Remove hífen seguido de espaço (to- morrow -> tomorrow), 
        # mas preserva hífens normais (Spider-Man).
        sniper_text = re.sub(r'-\s+', '', sniper_text)
        
        # 2. Filtra alucinações de caracteres japoneses/chineses (Kanji, Hiragana, Katakana)
        sniper_text = re.sub(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', '', sniper_text)
        
        # 3. Filtro de "Stuttering" (Repetição de caracteres)
        # Se uma letra se repete 4 ou mais vezes seguidas de forma anormal (ex: AAAAAAA), reduz para 3.
        sniper_text = re.sub(r'([a-zA-Z])\1{3,}', r'\1\1\1', sniper_text)
        
        # 4. Filtro Anti-Rachadura/Ruído Visual
        # Se a string contém pontuações mas NENHUMA letra/número, ignora completamente (vira vazio).
        if not re.search(r'[a-zA-Z0-9]', sniper_text) and len(re.findall(r'[^\w\s]', sniper_text)) > 0:
            sniper_text = ""
        
        if sniper_text.strip():
            global_bbox = [[crop_x1, crop_y1], [crop_x2, crop_y1], [crop_x2, crop_y2], [crop_x1, crop_y2]]
            sniper_clusters.append([{
                "bbox": global_bbox,
                "text": sniper_text,
                "confidence": 1.0,
                "center_x": (crop_x1 + crop_x2) / 2,
                "center_y": (crop_y1 + crop_y2) / 2,
                "min_y": crop_y1,
                "max_y": crop_y2,
                "min_x": crop_x1,
                "max_x": crop_x2,
                "height": crop_y2 - crop_y1,
                "cluster": -1
            }])
        else:
            sniper_clusters.append(cluster)
            
    clusters = sniper_clusters

    # Ordena clusters na ordem de leitura e junta texto
    texts = sort_and_merge_clusters(clusters, reading_order)

    # Removido: Descrição da cena para contexto multimodal (economia de VRAM)
    page_caption = ""
    
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return texts, page_caption

def generate_output(
    pages: list[dict],
    output_path: Path,
    append_mode: bool = False,
) -> None:
    """
    Gera o arquivo .txt de saída com o texto extraído.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if append_mode and output_path.exists():
        lines.append("")  # Adiciona linha extra no início para separar
        
    for page in pages:
        separator = "=" * 50
        lines.append(separator)
        lines.append(f"PÁGINA {page['number']}: {page['filename']}")
        lines.append(separator)
        lines.append("")

        if page.get("caption"):
            lines.append(f"[CONTEXT]: {page['caption']}")
            lines.append("")

        if page["texts"]:
            for text in page["texts"]:
                lines.append(text)
                lines.append("")
        else:
            lines.append("[Nenhum texto detectado nesta página]")
            lines.append("")

    content = "\n".join(lines)
    
    mode = "a" if append_mode else "w"
    with open(output_path, mode, encoding="utf-8-sig") as f:
        f.write(content)
        f.write("\n")


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

    # Inicializa Florence-2
    print("🚀 Inicializando Microsoft Florence-2-Large...")
    gpu_status = "GPU (CUDA)" if args.gpu else "CPU"
    print(f"   Dispositivo: {gpu_status}")
    print(f"   Modo: <OCR_WITH_REGION>")
    print()

    try:
        import torch
        import transformers.dynamic_module_utils
        transformers.dynamic_module_utils.check_imports = lambda filename: []
        from transformers import AutoProcessor, AutoModelForCausalLM
        from PIL import Image
        
        device = "cuda" if args.gpu and torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model_id = "microsoft/Florence-2-large"
        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch_dtype, trust_remote_code=True).to(device)
    except Exception as e:
        print(f"❌ Erro ao inicializar Florence-2: {e}")
        if args.gpu:
            print("   💡 Tente rodar sem --gpu, ou verifique se CUDA está instalado.")
        sys.exit(1)

    # Processa cada imagem
    print(f"🔄 Processando {len(images)} página(s)...")
    print(f"   Ordem de leitura: {'Manga (direita->esquerda)' if args.reading_order == 'manga' else 'Comic (esquerda->direita)'}")
    print()

    pages = []
    total_texts = 0
    start_time = time.time()

    for i, image_path in enumerate(images, 1):
        print(f"  [{i}/{len(images)}] 📄 {image_path.name}", end="", flush=True)

        page_start = time.time()
        texts, page_caption = process_image(
            image_path=image_path,
            model=model,
            processor=processor,
            device=device,
            torch_dtype=torch_dtype,
            reading_order=args.reading_order,
            verbose=args.verbose,
        )
        page_elapsed = time.time() - page_start

        pages.append({
            "number": i,
            "filename": image_path.name,
            "texts": texts,
            "caption": page_caption,
        })

        total_texts += len(texts)
        print(f"  ->  {len(texts)} texto(s)  ({page_elapsed:.1f}s)")

    elapsed = time.time() - start_time
    
    # Limpa VRAM
    if device == "cuda":
        torch.cuda.empty_cache()

    # Gera arquivo de saída
    generate_output(pages, output_path, append_mode=args.append)

    # Resumo
    print_summary(len(pages), total_texts, elapsed, output_path)

if __name__ == "__main__":
    main()
