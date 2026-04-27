import cv2
import pytesseract
from ultralytics import YOLO
import numpy as np
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

model = YOLO("best.pt")
cap = cv2.VideoCapture(0)

print("🚀 Sistema KYC de Z-Index Studio Iniciado.")
print("👉 ¡Haz clic en la ventana de video y presiona 'S' para escanear!")

while True:
    ret, frame = cap.read()
    if not ret: break

   
    results = model(frame, stream=True, conf=0.8, verbose=False)
    
    dni_limpio = None

    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            dni_crop = frame[y1:y2, x1:x2]

            if dni_crop.size > 0:
                
                gray = cv2.cvtColor(dni_crop, cv2.COLOR_BGR2GRAY)
                # Agrandar la imagen al doble 
                ampliado = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                # Mejorar el contraste
                dni_limpio = cv2.convertScaleAbs(ampliado, alpha=1.2, beta=0)

                cv2.imshow("Lo que lee la IA", dni_limpio)

        frame = r.plot()

    cv2.putText(frame, "Haz clic AQUI y presiona 'S'", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("KYC Scanner Pro - Z-Index Studio", frame)

    tecla = cv2.waitKey(1) & 0xFF
    
    if tecla == ord('s') and dni_limpio is not None:
        print("\n" + "="*40)
        print("📸 ¡FOTO CAPTURADA! Ejecutando extracción de datos MRZ...")
        
        configuracion = r'--oem 3 --psm 6'
        texto_crudo = pytesseract.image_to_string(dni_limpio, lang='spa', config=configuracion)
        

        texto_limpio = texto_crudo.replace(" ", "").replace("\n", "")


        match_dni = re.search(r'(\d{8})<(\d)', texto_limpio)
        if match_dni:
            dni_final = match_dni.group(1)
            cod_verificacion = match_dni.group(2)
        else:
            dni_final, cod_verificacion = "No detectado", "-"


        match_nacimiento = re.search(r'(\d{6})\d?([MF])', texto_limpio)
        if match_nacimiento:
            fecha_cruda = match_nacimiento.group(1)
            genero = match_nacimiento.group(2)
            
            anio = "20" + fecha_cruda[0:2]
            mes = fecha_cruda[2:4]
            dia = fecha_cruda[4:6]
            fecha_nacimiento = f"{dia}/{mes}/{anio}"
        else:
            fecha_nacimiento, genero = "No detectado", "-"

        match_nombre = re.search(r'([A-Z]+)<<([A-Z]+)<([A-Z]+)', texto_limpio)
        if match_nombre:
            apellidos = match_nombre.group(1)
            nombres = f"{match_nombre.group(2)} {match_nombre.group(3)}".replace("E<", "").strip()
        else:
            apellidos, nombres = "No detectado", "No detectado"

        print("✅ ¡DATOS DE SEGURIDAD ESTRUCTURADOS EXITOSAMENTE!")
        print(f"👤 Nombres       : {nombres}")
        print(f"👥 Apellidos     : {apellidos}")
        print(f"💳 DNI           : {dni_final} (Dígito Verificador: {cod_verificacion})")
        print(f"🎂 Nacimiento    : {fecha_nacimiento}")
        print(f"⚧️ Género        : {genero}")
        print("="*40 + "\n")
        
    elif tecla == ord('q') or tecla == 27:
        break

cap.release()
cv2.destroyAllWindows()