import cv2
import numpy as np

def test_balloon_detection(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Thresholding para achar fundo branco (balões)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    
    # Encontrar contornos
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    img_contours = img.copy()
    valid_contours = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1000: # Ignora ruidos pequenos
            valid_contours.append(cnt)
            cv2.drawContours(img_contours, [cnt], -1, (0, 255, 0), 2)
            
    cv2.imwrite("output/balloons_test.jpg", img_contours)
    print(f"Encontrados {len(valid_contours)} contornos validos.")

if __name__ == "__main__":
    test_balloon_detection(r"E:\Genikasuri\RAW\Chapter 011 - The Coach, Hung Up\009.png")
