import easyocr
import cv2
import time

def test_params(image_path):
    print("Carregando imagem...")
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Preprocessing test 1: Upscale + Binary Threshold
    # Manga text balloons are usually pure white background with black text
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    
    reader = easyocr.Reader(['en'], gpu=False) # CPU for quick test
    
    print("\n--- Teste 1: EasyOCR Default ---")
    t0 = time.time()
    res1 = reader.readtext(gray)
    print(f"Tempo: {time.time()-t0:.1f}s")
    for b, t, c in res1:
        if c > 0.1: print(t)
        
    print("\n--- Teste 2: EasyOCR com mag_ratio=2.0 (Upscaling interno) ---")
    t0 = time.time()
    res2 = reader.readtext(gray, mag_ratio=2.0, contrast_ths=0.1, adjust_contrast=0.5)
    print(f"Tempo: {time.time()-t0:.1f}s")
    for b, t, c in res2:
        if c > 0.1: print(t)
        
    print("\n--- Teste 3: EasyOCR Binarizado ---")
    t0 = time.time()
    res3 = reader.readtext(thresh, mag_ratio=1.5)
    print(f"Tempo: {time.time()-t0:.1f}s")
    for b, t, c in res3:
        if c > 0.1: print(t)

if __name__ == "__main__":
    test_params(r"E:\Genikasuri\RAW\Chapter 001 The Brazen Boxer\017.jpg")
