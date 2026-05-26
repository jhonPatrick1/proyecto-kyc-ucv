import cv2
import os

carpeta = "dataset_dni"
if not os.path.exists(carpeta):
    os.makedirs(carpeta)

cap = cv2.VideoCapture(0)
contador = 0

print("=========================================")
print("🤖 SISTEMA KYC (DATASET)")
print("👉 Presiona la tecla ESPACIO para tomar una foto.")
print("👉 Presiona la tecla ESC para salir.")
print("=========================================")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al acceder a la cámara. Verifica los permisos.")
        break

    
    cv2.putText(frame, f"Fotos: {contador}/100", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow("Captura de Dataset DNI", frame)

    tecla = cv2.waitKey(1)

    if tecla == 32: 
        ruta = os.path.join(carpeta, f"dni_{contador}.jpg")
        cv2.imwrite(ruta, frame)
        print(f"✅ Foto guardada: {ruta}")
        contador += 1

    elif tecla == 27 or contador >= 100: 
        print("🏁 Captura finalizada.")
        break

cap.release()
cv2.destroyAllWindows()