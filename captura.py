import cv2
import os

# 1. Crear la carpeta donde se guardarán tus fotos
carpeta = "dataset_dni"
if not os.path.exists(carpeta):
    os.makedirs(carpeta)

# 2. Encender la cámara web (el 0 es la cámara por defecto)
cap = cv2.VideoCapture(0)
contador = 0

print("=========================================")
print("🤖 Z-INDEX STUDIO - SISTEMA KYC (DATASET)")
print("👉 Presiona la tecla ESPACIO para tomar una foto.")
print("👉 Presiona la tecla ESC para salir.")
print("=========================================")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al acceder a la cámara. Verifica los permisos.")
        break

    # 3. Dibujar un texto en el video en vivo para ver el progreso
    cv2.putText(frame, f"Fotos: {contador}/100", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    # Mostrar la ventana
    cv2.imshow("Captura de Dataset DNI", frame)

    tecla = cv2.waitKey(1)

    # 4. Lógica de teclas
    if tecla == 32: # 32 es el código de la barra ESPACIADORA
        ruta = os.path.join(carpeta, f"dni_{contador}.jpg")
        cv2.imwrite(ruta, frame)
        print(f"✅ Foto guardada: {ruta}")
        contador += 1

    elif tecla == 27 or contador >= 100: # 27 es la tecla ESCAPE
        print("🏁 Captura finalizada.")
        break

# 5. Apagar la cámara y cerrar ventanas
cap.release()
cv2.destroyAllWindows()