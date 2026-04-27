from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import pytesseract
import re
from ultralytics import YOLO
from pymongo import MongoClient
import io
import certifi
from PIL import Image, ImageOps
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. CONEXIÓN A MONGO DB
MONGO_URI = "mongodb+srv://jhonpatrickcg_db_user:yHK7MkFlLeULjC23@cluster0.tknyeco.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["zindex_kyc_db"] 
coleccion = db["registros_dni"] 

# 2. CONFIGURACIÓN IA
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
model = YOLO("best.pt")

@app.post("/escanear")
async def escanear_dni(file: UploadFile = File(...)):
    # Leer la imagen que viene de internet/celular
    request_object_content = await file.read()
    img = Image.open(io.BytesIO(request_object_content))

    # --- EL FIX PARA CÁMARAS DE CELULARES ---
    # 1. Corregimos si el celular mandó la foto girada (EXIF)
    img = ImageOps.exif_transpose(img)
    # 2. Achicamos la foto a un máximo de 640px para que Render gratuito no colapse
    img.thumbnail((640, 640))
    # ----------------------------------------

    # Convertimos la imagen corregida para que OpenCV la pueda leer
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Detección con tu modelo YOLO
    results = model(frame, conf=0.8, verbose=False)
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            dni_crop = frame[y1:y2, x1:x2]

            # --- FILTROS DE VISIÓN ARTIFICIAL (CORREGIDOS) ---
            # 1. Blanco y Negro
            gray = cv2.cvtColor(dni_crop, cv2.COLOR_BGR2GRAY)
            # 2. Ampliamos la imagen al doble
            ampliado = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            # 3. Binarización pura (Umbral 120): Vuelve todo 100% blanco o 100% negro
            _, dni_limpio = cv2.threshold(ampliado, 120, 255, cv2.THRESH_BINARY)
            # ------------------------------------------------

            # OCR y Limpieza de texto
            texto_crudo = pytesseract.image_to_string(dni_limpio, lang='spa', config='--oem 3 --psm 6')
            texto_limpio = texto_crudo.replace(" ", "").replace("\n", "")

            # --- LÓGICA DE EXTRACCIÓN (RECUERDA: ESCANEAR PARTE TRASERA DEL DNI) ---
            
            # 1. DNI y Dígito Verificador (Ej: 72865658<5)
            match_dni = re.search(r'(\d{8})<(\d)', texto_limpio)
            dni_final = match_dni.group(1) if match_dni else "No detectado"
            digito_v = match_dni.group(2) if match_dni else "-"

            # 2. Fecha de Nacimiento y Género (Ej: 0410276M)
            match_nacimiento = re.search(r'(\d{6})\d?([MF])', texto_limpio)
            if match_nacimiento:
                fecha_cruda = match_nacimiento.group(1)
                genero_final = "Masculino" if match_nacimiento.group(2) == "M" else "Femenino"
                # Formato AAMMDD -> DD/MM/AAAA
                fecha_nac_final = f"{fecha_cruda[4:6]}/{fecha_cruda[2:4]}/20{fecha_cruda[0:2]}"
            else:
                fecha_nac_final, genero_final = "No detectado", "-"

            # 3. Nombres y Apellidos
            match_nombre = re.search(r'([A-Z]+)<<([A-Z]+)<([A-Z]+)', texto_limpio)
            if match_nombre:
                apellidos = match_nombre.group(1)
                nombres = f"{match_nombre.group(2)} {match_nombre.group(3)}".replace("E<", "").strip()
            else:
                apellidos, nombres = "No detectado", "No detectado"

            # 3. GUARDAR EN MONGO DB (Documento Completo)
            documento = {
                "nombres": nombres,
                "apellidos": apellidos,
                "dni": dni_final,
                "digito_verificador": digito_v,
                "fecha_nacimiento": fecha_nac_final,
                "genero": genero_final,
                "estado": "Verificado",
                "agencia": "Proyecto Universitario"
            }
            
            # Insertamos en la nube
            resultado = coleccion.insert_one(documento)
            
            # Convertimos el ID de Mongo a un texto normal para la respuesta
            documento["_id"] = str(resultado.inserted_id)
            
            print(f"✅ Registro Completo Guardado: {dni_final} ({nombres})")

            return {
                "status": "success",
                "datos": documento
            }
            
    return {"status": "error", "message": "No se detectó DNI"}

@app.get("/registros")
async def obtener_registros():
    # Buscamos todos los registros y los ordenamos por el más reciente
    registros_db = coleccion.find().sort("_id", -1) 
    lista_registros = []
    
    for doc in registros_db:
        doc["_id"] = str(doc["_id"]) # Convertimos el ID para evitar errores
        lista_registros.append(doc)
        
    return {"status": "success", "data": lista_registros}


if __name__ == "__main__":
    import uvicorn
    # Levantamos el servidor en el puerto 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)