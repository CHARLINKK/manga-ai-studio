"""
Script para gerar uma imagem de teste simulando uma página de mangá com balões de fala.
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_test_page():
    # Cria imagem branca (simula página de mangá)
    width, height = 800, 1200
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Tenta usar uma fonte do sistema, senão usa default
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Desenha painéis (retângulos)
    # Painel superior direito (lido primeiro em mangá)
    draw.rectangle([410, 20, 780, 380], outline="black", width=3)
    # Painel superior esquerdo
    draw.rectangle([20, 20, 390, 380], outline="black", width=3)
    # Painel inferior
    draw.rectangle([20, 400, 780, 780], outline="black", width=3)
    # Painel inferior 2
    draw.rectangle([20, 800, 780, 1180], outline="black", width=3)

    # Balões de fala (elipses)
    # Balão 1 - painel superior direito
    draw.ellipse([450, 40, 760, 160], fill="white", outline="black", width=2)
    draw.text((500, 70), "I can't believe\nyou said that!", fill="black", font=font)

    # Balão 2 - painel superior esquerdo
    draw.ellipse([40, 80, 370, 180], fill="white", outline="black", width=2)
    draw.text((80, 100), "What do you mean?", fill="black", font=font)

    # Balão 3 - painel inferior
    draw.ellipse([60, 420, 450, 540], fill="white", outline="black", width=2)
    draw.text((110, 450), "It's not what\nyou think...", fill="black", font=font)

    # Balão 4 - painel inferior direito
    draw.ellipse([460, 500, 760, 600], fill="white", outline="black", width=2)
    draw.text((500, 520), "Let's go!", fill="black", font=font)

    # Balão 5 - painel inferior 2
    draw.ellipse([100, 850, 700, 1000], fill="white", outline="black", width=2)
    draw.text((180, 880), "We don't have time\n    for this!", fill="black", font=font)

    # Salva
    test_dir = os.path.join(os.path.dirname(__file__), "test_pages")
    os.makedirs(test_dir, exist_ok=True)
    output_path = os.path.join(test_dir, "test_page_001.png")
    img.save(output_path, "PNG")
    print(f"Imagem de teste criada: {output_path}")
    return output_path

if __name__ == "__main__":
    create_test_page()
