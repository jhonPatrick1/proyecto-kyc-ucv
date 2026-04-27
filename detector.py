import cv2
from ultralytics import YOLO

# 1. Cargar el cerebro que acabas de entrenar
print("Cargando redes neuronales...")
model = YOLO("best.pt")

# 2. Encender la cámara web
cap = cv2.VideoCapture(0)

print("=========================================")
print("🤖 Z-INDEX STUDIO - IA KYC ACTIVADA")
print("👉 Muestra el DNI a la cámara.")
print("👉 Presiona la tecla 'q' o ESC para salir.")
print("=========================================")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al acceder a la cámara.")
        break

    # 3. La IA analiza el video frame por frame en tiempo real
    # conf=0.5 significa que solo mostrará la caja si está al menos 50% segura de que es un DNI
    resultados = model(frame, stream=True, conf=0.5) 

    # 4. Dibujar las cajas predictivas automáticamente
    for r in resultados:
        # La librería de YOLO tiene un método .plot() que dibuja todo por nosotros
        frame_dibujado = r.plot()

    # Mostrar la ventana con el resultado en vivo
    cv2.imshow("Scanner KYC", frame_dibujado)

    # 5. Lógica para cerrar el programa
    tecla = cv2.waitKey(1)
    if tecla == ord('q') or tecla == 27:
        break

# Limpiar los procesos al salir
cap.release()
cv2.destroyAllWindows()