import cv2
from ultralytics import YOLO

print("Cargando redes neuronales...")
model = YOLO("best.pt")

cap = cv2.VideoCapture(0)

print("=========================================")
print("🤖 IA KYC ACTIVADA")
print("👉 Muestra el DNI a la cámara.")
print("👉 Presiona la tecla 'q' o ESC para salir.")
print("=========================================")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al acceder a la cámara.")
        break

    resultados = model(frame, stream=True, conf=0.5) 
 
    for r in resultados:

        frame_dibujado = r.plot()
    
    cv2.imshow("Scanner KYC", frame_dibujado)

    tecla = cv2.waitKey(1)
    if tecla == ord('q') or tecla == 27:
        break

cap.release()
cv2.destroyAllWindows()