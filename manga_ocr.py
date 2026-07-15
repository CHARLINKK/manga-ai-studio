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
os.environ["HF_HOME"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "huggingface")

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

    parser.add_argument(
        "--vlm-director",
        action="store_true",
        help="Ativa o Diretor Visual (Qwen2.5-VL-7B) para corrigir ordem de leitura e remover onomatopeias. Requer ~5.5GB VRAM livre após Florence-2.",
    )
    parser.add_argument(
        "--vlm-model",
        type=str,
        default="Qwen/Qwen2.5-VL-7B-Instruct",
        help="ID do modelo VLM a usar como Diretor Visual. Padrão: Qwen/Qwen2.5-VL-7B-Instruct",
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


# ---------------------------------------------------------------------------
# LEITURA ORDENADA — SISTEMA EM 3 CAMADAS
# Camada 1: detect_panels        → OpenCV detecta bordas de painéis
# Camada 2: sort_clusters_by_panels  → ordena clusters por painel (Opção B)
# Camada 3: sort_clusters_by_overlap → fallback por sobreposição Y (Opção A)
# Orquestrador: sort_and_merge_clusters escolhe qual usar
# ---------------------------------------------------------------------------


def _group_consecutive(indices: list[int], gap: int = 5) -> list[tuple[int, int]]:
    """
    Agrupa índices consecutivos em bandas (start, end).
    Usada internamente por detect_panels.
    """
    if not indices:
        return []
    bands = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if idx - prev <= gap:
            prev = idx
        else:
            bands.append((start, prev))
            start = prev = idx
    bands.append((start, prev))
    return bands


def detect_panels(image_pil) -> tuple[list[dict], float]:
    """
    Detecta os painéis de uma página de mangá usando OpenCV.

    Procura faixas brancas (≥240) horizontais e verticais que formam
    as 'calhas' (gutters) entre os painéis.

    Retorna:
        panels      : lista de dicts com chaves x1, y1, x2, y2
        confidence  : float 0.0–1.0 indicando certeza da detecção
    """
    img_np = np.array(image_pil.convert("L"))  # grayscale
    h, w = img_np.shape

    # --- 1. Threshold: isola pixels muito claros (bordas brancas dos painéis) ---
    _, binary = cv2.threshold(img_np, 235, 255, cv2.THRESH_BINARY)

    # --- 2. Separadores horizontais: linhas onde >75% dos pixels são brancos ---
    row_means = binary.mean(axis=1)
    h_sep_indices = [i for i, m in enumerate(row_means) if m > 190]
    h_bands = _group_consecutive(h_sep_indices, gap=8)
    # Filtra bandas de ruído (< 3px de espessura)
    h_bands = [(s, e) for s, e in h_bands if (e - s) >= 2]

    # --- 3. Separadores verticais: colunas onde >75% dos pixels são brancos ---
    col_means = binary.mean(axis=0)
    v_sep_indices = [i for i, m in enumerate(col_means) if m > 190]
    v_bands = _group_consecutive(v_sep_indices, gap=8)
    v_bands = [(s, e) for s, e in v_bands if (e - s) >= 2]

    # --- 4. Cria grade de painéis a partir das faixas separadoras ---
    # Adiciona bordas da imagem como separadores virtuais
    h_cuts = [0] + [int((s + e) / 2) for s, e in h_bands] + [h]
    v_cuts = [0] + [int((s + e) / 2) for s, e in v_bands] + [w]

    panels = []
    for i in range(len(h_cuts) - 1):
        for j in range(len(v_cuts) - 1):
            p = {
                "x1": v_cuts[j],
                "y1": h_cuts[i],
                "x2": v_cuts[j + 1],
                "y2": h_cuts[i + 1],
            }
            panel_w = p["x2"] - p["x1"]
            panel_h = p["y2"] - p["y1"]
            # Descarta painéis ridiculamente pequenos (< 3% da imagem)
            if panel_w * panel_h > (w * h * 0.03):
                panels.append(p)

    # --- 5. Score de confiança ---
    confidence = 1.0

    if len(panels) < 2:
        return [], 0.0

    # Penaliza se poucos separadores foram encontrados
    if len(h_bands) == 0 and len(v_bands) == 0:
        confidence -= 0.5

    # Penaliza painéis com aspect ratio absurdo (> 12:1 ou < 1:12)
    bad_ar = sum(
        1 for p in panels
        if (p["x2"] - p["x1"]) > 0 and
           ((p["y2"] - p["y1"]) / (p["x2"] - p["x1"]) > 12 or
            (p["x2"] - p["x1"]) / max(p["y2"] - p["y1"], 1) > 12)
    )
    confidence -= bad_ar * 0.1

    # Penaliza se área total dos painéis cobre < 70% da imagem
    total_panel_area = sum((p["x2"] - p["x1"]) * (p["y2"] - p["y1"]) for p in panels)
    coverage = total_panel_area / (w * h)
    if coverage < 0.70:
        confidence -= 0.2

    confidence = max(0.0, min(1.0, confidence))
    return panels, confidence


def _merge_cluster_text(cluster: list, cluster_info: dict) -> str:
    """
    Junta o texto de um cluster em uma string, tratando hifens de quebra de linha.
    Aplica filtros de ruído antes de retornar.
    """
    blocks_sorted = sorted(cluster_info["blocks"], key=lambda b: b["min_y"])
    merged = ""
    lines = [b["text"].strip() for b in blocks_sorted]
    for i, line in enumerate(lines):
        if line.endswith("-") and i < len(lines) - 1:
            merged += line[:-1]
        else:
            merged += line + (" " if i < len(lines) - 1 else "")
    merged = merged.strip()

    # Filtros de ruído
    merged_upper = merged.upper()
    denylist = ['2MB', '1MB', '3MB', '4MB', '5MB', '000', 'OOO']
    if merged_upper in denylist:
        return ""
    if len(merged) == 1 and merged_upper not in ['I', 'A', 'O', '?', '!']:
        return ""
    if len(merged) <= 2 and not any(c.isalpha() for c in merged):
        if not any(c in '?!' for c in merged):
            return ""
    return merged


def _get_consecutive_trues(bool_array, min_length=5):
    """Retorna lista de tuplas (start, end) para sequências de True em um array."""
    gaps = []
    start = None
    for i, val in enumerate(bool_array):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start >= min_length:
                gaps.append((start, i))
            start = None
    if start is not None and len(bool_array) - start >= min_length:
        gaps.append((start, len(bool_array)))
    return gaps

def recursive_xy_cut(binary_image, x1, y1, x2, y2, min_w, min_h, reading_order="manga"):
    """
    Algoritmo de Corte XY Recursivo para detectar painéis de mangá.
    Alterna entre cortes horizontais e verticais nas calhas brancas.
    Retorna a lista de painéis já na ORDEM DE LEITURA CORRETA!
    """
    if x2 - x1 < min_w or y2 - y1 < min_h:
        return [{"x1": x1, "y1": y1, "x2": x2, "y2": y2}]
        
    region = binary_image[y1:y2, x1:x2]
    
    # 1. Tenta corte Horizontal (procura calha branca que cruza toda a largura)
    row_means = region.mean(axis=1)
    # Considera calha se a linha for > 95% branca (242/255)
    h_gaps = _get_consecutive_trues(row_means > 242, min_length=8)
    
    if h_gaps:
        panels = []
        current_y = y1
        for gap_start, gap_end in h_gaps:
            mid_y = y1 + (gap_start + gap_end) // 2
            if mid_y - current_y >= min_h:
                # Top to Bottom
                panels.extend(recursive_xy_cut(binary_image, x1, current_y, x2, mid_y, min_w, min_h, reading_order))
            current_y = y1 + gap_end
            
        if y2 - current_y >= min_h:
            panels.extend(recursive_xy_cut(binary_image, x1, current_y, x2, y2, min_w, min_h, reading_order))
        return panels
        
    # 2. Tenta corte Vertical (procura calha branca que cruza toda a altura)
    col_means = region.mean(axis=0)
    v_gaps = _get_consecutive_trues(col_means > 242, min_length=8)
    
    if v_gaps:
        panels = []
        current_x = x1
        for gap_start, gap_end in v_gaps:
            mid_x = x1 + (gap_start + gap_end) // 2
            if mid_x - current_x >= min_w:
                panels.append(recursive_xy_cut(binary_image, current_x, y1, mid_x, y2, min_w, min_h, reading_order))
            current_x = x1 + gap_end
            
        if x2 - current_x >= min_w:
            panels.append(recursive_xy_cut(binary_image, current_x, y1, x2, y2, min_w, min_h, reading_order))
            
        # Achata a lista
        flat_panels = []
        # Right to Left para Manga, Left to Right para Comic
        if reading_order == "manga":
            panels.reverse()
            
        for p_list in panels:
            flat_panels.extend(p_list)
        return flat_panels
        
    # Sem cortes possíveis (painel indivisível)
    return [{"x1": x1, "y1": y1, "x2": x2, "y2": y2}]

def detect_panels_recursive(image_pil, reading_order="manga") -> list[dict]:
    import numpy as np
    import cv2
    img_np = np.array(image_pil.convert("L"))
    _, binary = cv2.threshold(img_np, 235, 255, cv2.THRESH_BINARY)
    
    h, w = binary.shape
    min_w = w * 0.10
    min_h = h * 0.05
    
    panels = recursive_xy_cut(binary, 0, 0, w, h, min_w, min_h, reading_order)
    return panels

def sort_clusters_by_recursive_panels(
    cluster_info: list[dict],
    panels: list[dict],
    reading_order: str = "manga"
) -> list[dict]:
    """
    Atribui os balões aos painéis recursivos e usa o fallback dentro de cada painel.
    Os painéis já vêm ordenados corretamente da função recursive_xy_cut.
    """
    if not panels or len(panels) < 2:
        return sort_clusters_by_overlap(cluster_info, reading_order)
        
    for ci in cluster_info:
        ci["cluster_min_y"] = min(b["min_y"] for b in ci["blocks"])
        ci["cluster_max_y"] = max(b["max_y"] for b in ci["blocks"])
        
    from collections import defaultdict
    panel_to_clusters = defaultdict(list)
    orphans = []
    
    for ci in cluster_info:
        cx = ci["avg_x"]
        cy = (ci["cluster_min_y"] + ci["cluster_max_y"]) / 2
        assigned = False
        for pidx, p in enumerate(panels):
            if p["x1"] <= cx <= p["x2"] and p["y1"] <= cy <= p["y2"]:
                panel_to_clusters[pidx].append(ci)
                assigned = True
                break
        if not assigned:
            orphans.append(ci)
            
    ordered = []
    # Os painéis JÁ ESTÃO ordenados do Recursive XY-Cut
    for pidx in range(len(panels)):
        if pidx in panel_to_clusters:
            # Ordena balões DENTRO do painel
            ordered.extend(sort_clusters_by_overlap(panel_to_clusters[pidx], reading_order))
            
    if orphans:
        ordered.extend(sort_clusters_by_overlap(orphans, reading_order))
        
    return ordered


def sort_clusters_by_overlap(
    cluster_info: list[dict],
    reading_order: str = "manga",
) -> list[dict]:
    """
    Opção A — Fallback: agrupa clusters por sobreposição vertical de bounding box.

    Dois clusters vão para a mesma 'linha de leitura' se seus intervalos Y
    se sobrepõem em pelo menos 15% da altura do menor cluster.
    Isso resolve casos onde dois balões são lado a lado mas têm Y diferentes.
    """
    if not cluster_info:
        return []

    n = len(cluster_info)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    # Enriquece cluster_info com min_y/max_y do cluster inteiro
    for ci in cluster_info:
        ci["cluster_min_y"] = min(b["min_y"] for b in ci["blocks"])
        ci["cluster_max_y"] = max(b["max_y"] for b in ci["blocks"])

    # Union-Find: une clusters com sobreposição vertical >= 15%
    for i in range(n):
        for j in range(i + 1, n):
            a = cluster_info[i]
            b = cluster_info[j]
            overlap = min(a["cluster_max_y"], b["cluster_max_y"]) - max(a["cluster_min_y"], b["cluster_min_y"])
            min_height = min(
                a["cluster_max_y"] - a["cluster_min_y"],
                b["cluster_max_y"] - b["cluster_min_y"]
            )
            if min_height > 0 and overlap / min_height >= 0.15:
                union(i, j)

    # Agrupa por componente
    from collections import defaultdict
    groups: dict[int, list[dict]] = defaultdict(list)
    for i, ci in enumerate(cluster_info):
        groups[find(i)].append(ci)

    # Ordena grupos pelo Y médio do grupo (top-to-bottom)
    sorted_groups = sorted(groups.values(), key=lambda g: min(c["cluster_min_y"] for c in g))

    # Dentro de cada grupo, ordena por X (manga: direita→esquerda)
    ordered = []
    for group in sorted_groups:
        if reading_order == "manga":
            group_sorted = sorted(group, key=lambda c: c["avg_x"], reverse=True)
        else:
            group_sorted = sorted(group, key=lambda c: c["avg_x"])
        ordered.extend(group_sorted)

    return ordered


def sort_clusters_by_panels(
    cluster_info: list[dict],
    panels: list[dict],
    reading_order: str = "manga",
) -> list[dict]:
    """
    Opção B — Principal: ordena clusters com base nos painéis detectados pelo OpenCV.

    Fluxo:
      1. Atribui cada cluster ao painel que contém seu centro
      2. Ordena painéis: top-to-bottom; painéis na mesma linha → direita-p-esquerda (manga)
      3. Dentro de cada painel, ordena clusters por X (manga: desc)
      4. Clusters sem painel (orphans) → tratados pelo sort_clusters_by_overlap localmente
    """
    if not panels:
        return sort_clusters_by_overlap(cluster_info, reading_order)

    # Enriquece cluster_info
    for ci in cluster_info:
        ci["cluster_min_y"] = min(b["min_y"] for b in ci["blocks"])
        ci["cluster_max_y"] = max(b["max_y"] for b in ci["blocks"])

    # --- Atribui clusters a painéis ---
    from collections import defaultdict
    panel_to_clusters: dict[int, list[dict]] = defaultdict(list)
    orphans: list[dict] = []

    for ci in cluster_info:
        cx = ci["avg_x"]
        cy = (ci["cluster_min_y"] + ci["cluster_max_y"]) / 2
        assigned = False
        for pidx, panel in enumerate(panels):
            if panel["x1"] <= cx <= panel["x2"] and panel["y1"] <= cy <= panel["y2"]:
                panel_to_clusters[pidx].append(ci)
                assigned = True
                break
        if not assigned:
            orphans.append(ci)

    # --- Ordena os painéis por posição de leitura ---
    # Agrupa painéis em linhas usando o UNION do range Y de toda a linha como referência.
    # Isso evita que painéis do mesmo nível (2-E e 2-D) sejam separados quando um painel
    # de outra linha tem y1/y2 próximo a apenas UM dos painéis do grupo.
    sorted_panels = sorted(enumerate(panels), key=lambda x: x[1]["y1"])
    panel_rows = []
    current_row = [sorted_panels[0]]
    for pidx, panel in sorted_panels[1:]:
        # Referência = union de todos os painéis já na linha atual
        row_y1 = min(p[1]["y1"] for p in current_row)
        row_y2 = max(p[1]["y2"] for p in current_row)
        # Dois painéis estão na mesma linha se overlap Y >= 20% do MENOR dos dois
        overlap = min(row_y2, panel["y2"]) - max(row_y1, panel["y1"])
        min_h = min(row_y2 - row_y1, panel["y2"] - panel["y1"])
        if min_h > 0 and overlap / min_h >= 0.20:
            current_row.append((pidx, panel))
        else:
            panel_rows.append(current_row)
            current_row = [(pidx, panel)]
    panel_rows.append(current_row)

    # Dentro de cada linha de painéis, ordena por X (manga: direita→esquerda)
    ordered_panels = []
    for row in panel_rows:
        if reading_order == "manga":
            row_sorted = sorted(row, key=lambda x: x[1]["x1"], reverse=True)
        else:
            row_sorted = sorted(row, key=lambda x: x[1]["x1"])
        ordered_panels.extend(row_sorted)

    # --- Monta lista final de clusters ordenados ---
    ordered: list[dict] = []
    for pidx, _ in ordered_panels:
        cs = panel_to_clusters.get(pidx, [])
        if not cs:
            continue
        # Dentro do painel, ordena por X
        if reading_order == "manga":
            cs_sorted = sorted(cs, key=lambda c: c["avg_x"], reverse=True)
        else:
            cs_sorted = sorted(cs, key=lambda c: c["avg_x"])
        ordered.extend(cs_sorted)

    # Orphans no final, ordenados por overlap
    if orphans:
        ordered.extend(sort_clusters_by_overlap(orphans, reading_order))

    return ordered


def sort_and_merge_clusters(
    clusters: list[list],
    reading_order: str = "manga",
    panels: list[dict] | None = None,
    verbose: bool = False,
) -> list[str]:
    """
    Orquestrador da ordenação de leitura.

    - Se `panels` for fornecido e tiver >= 2 painéis → usa sort_clusters_by_panels (Opção B)
    - Caso contrário → usa sort_clusters_by_overlap (Opção A, fallback)

    Depois de ordenar, junta o texto de cada cluster e aplica filtros de ruído.
    """
    if not clusters:
        return []

    # Constrói cluster_info com metadados de posição
    cluster_info = []
    for cluster in clusters:
        avg_x = sum(b["center_x"] for b in cluster) / len(cluster)
        avg_y = sum(b["min_y"] for b in cluster) / len(cluster)
        cluster_info.append({
            "blocks": cluster,
            "avg_x": avg_x,
            "avg_y": avg_y,
        })

    # Escolhe estratégia de ordenação
    if panels and len(panels) >= 2:
        if verbose:
            print(f"  🗂️  Ordenando por {len(panels)} painéis estruturais (XY-Cut)")
        ordered = sort_clusters_by_recursive_panels(cluster_info, panels, reading_order)
    else:
        if verbose:
            print("  🔀  Ordenando por sobreposição vertical (fallback global)")
        ordered = sort_clusters_by_overlap(cluster_info, reading_order)

    # Gera textos finais
    sorted_texts = []
    for ci in ordered:
        merged = _merge_cluster_text(ci["blocks"], ci)
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
        return [], ""

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

    # Usa Recursive XY-Cut para detectar painéis hierárquicos!
    panels = detect_panels_recursive(image, reading_order)
    if verbose:
        print(f"  🗂️  {len(panels)} painéis estruturais identificados.")

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
    texts = sort_and_merge_clusters(
        clusters,
        reading_order,
        panels=panels,
        verbose=verbose,
    )

    # Removido: Descrição da cena para contexto multimodal (economia de VRAM)
    page_caption = ""
    
    import torch
    if torch.cuda.is_available():
        try:
            del inputs, generated_ids, generated_text, results
        except NameError:
            pass
        torch.cuda.empty_cache()

    return texts, page_caption


# ===========================================================================
#  DIRETOR VISUAL DE LEITURA (Camada 1 — VLM Local)
# ===========================================================================

# Padrões para detecção de onomatopeias (Camada 2 — Corretor de Texto)
_SFX_PATTERNS = [
    r"^[A-Z]{2,}[!\.\?\s]*$",              # BOOM!, CRASH, BAM...
    r"^[A-Z][a-z]{0,2}[A-Z]+[!\.\?]*$",   # BaM!, CrASH
    r"^(Swirl|Whoosh|Thud|Clang|Bam|Pow|Zap|Crack|Slam|Bang|Thwack|Smash|Crunch|Rumble|Swoosh|Whack|Kapow)[\!\.\?]*$",
    r"^\W+$",                               # Só pontuação
]

def _is_onomatopeia(text: str) -> bool:
    """Verifica se um texto é provavelmente uma onomatopeia via padrões regex (Camada 2)."""
    import re
    t = text.strip()
    if not t or len(t) > 30:  # Onomatopeias são curtas
        return False
    for pattern in _SFX_PATTERNS:
        if re.match(pattern, t):
            return True
    return False


def apply_vlm_reading_director(
    image,
    ordered_texts: list[str],
    vlm_model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct",
    device: str = "cuda",
    verbose: bool = False,
) -> list[str]:
    """
    Diretor Visual de Leitura (Camada 1).

    Recebe a imagem da página + textos já ordenados geometricamente pelo Florence-2
    e usa um VLM (Qwen2.5-VL) para:
    1. Verificar/corrigir a ordem de leitura analisando a imagem visualmente.
    2. Identificar e remover onomatopeias (SFX) da lista final.

    Retorna a lista de textos reordenada e filtrada.
    Usa fallback para a ordem geométrica se o VLM falhar.
    """
    import re
    import json
    import torch

    if not ordered_texts:
        return ordered_texts

    if verbose:
        print(f"  🎬  Diretor Visual: analisando {len(ordered_texts)} texto(s)...")

    try:
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        from qwen_vl_utils import process_vision_info

        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        vlm_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            vlm_model_id,
            torch_dtype=torch_dtype,
            attn_implementation="sdpa",
            device_map=device,
        )
        vlm_processor = AutoProcessor.from_pretrained(vlm_model_id)

        # Monta lista numerada de textos para o prompt
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(ordered_texts))

        system_prompt = (
            "Você é um árbitro especializado em ordem de leitura de mangás japoneses.\n"
            "Você recebe uma imagem de página de mangá e uma lista numerada de textos extraídos.\n"
            "Suas regras:\n"
            "- Mangá é lido da DIREITA para ESQUERDA, de cima para baixo.\n"
            "- Leia painel por painel, sempre da direita para a esquerda dentro de cada painel.\n"
            "- NÃO modifique, corrija ou invente nenhum texto.\n"
            "- Classifique cada item como 'speech' (fala de personagem) ou 'sfx' (efeito sonoro/onomatopeia).\n"
            "  Exemplos de 'sfx': BOOM, SWIRL, CRASH, BAM, THUD, Swirl, BWAHAHA (risada).\n"
            "  Exemplos de 'speech': qualquer frase com sentido de diálogo.\n"
            "- Retorne SOMENTE um JSON válido, sem texto adicional.\n"
            "  Formato: {\"order\": [índices na ordem correta], \"sfx\": [índices de SFX a remover]}\n"
            "  Exemplo: {\"order\": [1, 3, 2, 4, 5], \"sfx\": [3]}\n"
            "  Os índices em 'sfx' DEVEM estar ausentes de 'order'.\n"
        )

        user_content = [
            {"type": "image", "image": image},
            {"type": "text", "text": f"Aqui estão os textos extraídos:\n{numbered}\n\nAnalise a imagem e retorne o JSON com a ordem correta e os SFX identificados."}
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        text_input = vlm_processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = vlm_processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            generated_ids = vlm_model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated_ids)]
        output_text = vlm_processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        # Descarrega VLM da VRAM imediatamente após uso
        del vlm_model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Parse do JSON
        json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
        if not json_match:
            raise ValueError(f"VLM não retornou JSON válido: {output_text[:200]}")

        result = json.loads(json_match.group())
        order = result.get("order", [])
        sfx_indices = set(result.get("sfx", []))

        # Valida índices
        n = len(ordered_texts)
        valid_order = [i for i in order if isinstance(i, int) and 1 <= i <= n and i not in sfx_indices]

        # Adiciona textos não mencionados no final (safety net)
        mentioned = set(order)
        for i in range(1, n + 1):
            if i not in mentioned and i not in sfx_indices:
                valid_order.append(i)

        reordered = [ordered_texts[i - 1] for i in valid_order]

        # Camada 2: filtro regex para SFX que escaparam do VLM
        reordered = [t for t in reordered if not _is_onomatopeia(t)]

        if verbose:
            removed = len(ordered_texts) - len(reordered)
            print(f"  ✅  Diretor Visual: ordem corrigida, {len(sfx_indices)} SFX removidos pelo VLM, {removed - len(sfx_indices)} pelo filtro regex.")

        return reordered

    except Exception as e:
        if verbose:
            print(f"  ⚠️  Diretor Visual falhou ({e}), usando ordem geométrica + filtro regex.")
        # Fallback: só aplica a Camada 2 (regex)
        return [t for t in ordered_texts if not _is_onomatopeia(t)]



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
        model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            torch_dtype=torch_dtype, 
            trust_remote_code=True,
            device_map=device
        )
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
    
    # Descarrega Florence-2 da VRAM antes do Diretor Visual
    del model, processor
    if device == "cuda":
        import torch
        torch.cuda.empty_cache()

    # Diretor Visual de Leitura (Camada 1 — VLM)
    if args.vlm_director:
        from PIL import Image
        vlm_device = "cuda" if args.gpu and __import__('torch').cuda.is_available() else "cpu"
        print()
        print(f"🎬 Iniciando Diretor Visual ({args.vlm_model})...")
        for page in pages:
            try:
                img = Image.open(collect_images(args.input)[pages.index(page)]).convert("RGB")
            except Exception as e:
                print(f"  [SKIP] Imagem ignorada no Diretor Visual (erro de carregamento): {e}")
                continue
                
            page["texts"] = apply_vlm_reading_director(
                image=img,
                ordered_texts=page["texts"],
                vlm_model_id=args.vlm_model,
                device=vlm_device,
                verbose=args.verbose,
            )
        print("  ✅ Diretor Visual concluído.")
    else:
        # Mesmo sem o VLM, aplica o filtro regex de onomatopeias (Camada 2)
        for page in pages:
            page["texts"] = [t for t in page["texts"] if not _is_onomatopeia(t)]

    # Gera arquivo de saída
    generate_output(pages, output_path, append_mode=args.append)

    # Resumo
    total_texts = sum(len(p["texts"]) for p in pages)
    print_summary(len(pages), total_texts, elapsed, output_path)

if __name__ == "__main__":
    main()
