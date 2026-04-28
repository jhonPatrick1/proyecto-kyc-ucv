from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import pytesseract
import re
from ultralytics import YOLO
from pymongo import MongoClient
from bson import ObjectId
import io
import certifi
import requests
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
model = YOLO("best.pt")

@app.post("/escanear")
async def escanear_dni(file: UploadFile = File(...)):
    # Leer la imagen
    request_object_content = await file.read()
    img = Image.open(io.BytesIO(request_object_content))
    
    # Optimización para celulares (Rotación y Memoria RAM)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((640, 640))
    
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Usamos conf=0.5 para que la IA sea más permisiva con fotos de celular
    results = model(frame, conf=0.5, verbose=False)
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            dni_crop = frame[y1:y2, x1:x2]
            
            # --- Filtros de Visión (Nivel Pro con Otsu) ---
            gray = cv2.cvtColor(dni_crop, cv2.COLOR_BGR2GRAY)
            ampliado = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            blur = cv2.GaussianBlur(ampliado, (3, 3), 0)
            _, dni_limpio = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # --- OCR en modo "Cazador" (psm 11) ---
            texto_crudo = pytesseract.image_to_string(dni_limpio, lang='spa', config='--oem 3 --psm 11')
            texto_limpio = texto_crudo.replace(" ", "").replace("\n", "").upper()

            # --- LÓGICA DE EXTRACCIÓN SÚPER MEJORADA (A PRUEBA DE BALAS) ---
            dni_final = "No detectado"

            # Intento 1: La franja frontal (Ej: PER09947694) - Ignoramos el '<' y aceptamos la 'O'
            match_frontal = re.search(r'PER([0-9O]{8})', texto_limpio)
            
            # Intento 2: DNI rojo superior (Ej: DNI09947694)
            match_rojo = re.search(r'DNI([0-9O]{8})', texto_limpio)

            # Intento 3: La parte trasera clásica (Ej: 72865658<5 o 72865658C5)
            match_trasera = re.search(r'([0-9O]{8})[<CKE(]+(\d)', texto_limpio)

            if match_frontal:
                dni_final = match_frontal.group(1).replace("O", "0")
                print(f"🎯 DNI detectado (Franja PER): {dni_final}")
            elif match_rojo:
                dni_final = match_rojo.group(1).replace("O", "0")
                print(f"🎯 DNI detectado (Rojo superior): {dni_final}")
            elif match_trasera:
                dni_final = match_trasera.group(1).replace("O", "0")
                print(f"🎯 DNI detectado (Trasera): {dni_final}")

            # --- CONSULTA A API RENIEC (apis.net.pe) ---
            nombres, apellidos, verificacion = "No detectado", "No detectado", "No verificado"

            if dni_final != "No detectado":
                try:
                    response = requests.get(f"https://api.apis.net.pe/v1/dni?numero={dni_final}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        nombres = data.get("nombres", "No detectado")
                        apellidos = f"{data.get('apellidoPaterno', '')} {data.get('apellidoMaterno', '')}".strip()
                        verificacion = "Verificado por RENIEC"
                        print(f"🌟 API Exitosa: {nombres}")
                    else:
                        verificacion = "DNI no encontrado en padrón"
                except Exception as e:
                    verificacion = "Error de conexión con API"
                    print(f"Error API: {e}")

            # Extracción de Fecha y Género (Suele funcionar mejor en la trasera)
            match_nacimiento = re.search(r'(\d{6})\d?([MF])', texto_limpio)
            if match_nacimiento:
                fecha_cruda = match_nacimiento.group(1)
                genero_final = "Masculino" if match_nacimiento.group(2) == "M" else "Femenino"
                fecha_nac_final = f"{fecha_cruda[4:6]}/{fecha_cruda[2:4]}/20{fecha_cruda[0:2]}"
            else:
                fecha_nac_final, genero_final = "No detectado", "-"

            # Solo guardamos lo necesario en la Base de Datos
            documento = {
                "nombres": nombres,
                "apellidos": apellidos,
                "dni": dni_final,
                "fecha_nacimiento": fecha_nac_final,
                "genero": genero_final,
                "validacion": verificacion
            }
            
            resultado = coleccion.insert_one(documento)
            documento["_id"] = str(resultado.inserted_id)
            
            return {"status": "success", "datos": documento}
            
    return {"status": "error", "message": "No se detectó un DNI válido o legible"}

@app.get("/registros")
async def obtener_registros():
    registros_db = coleccion.find().sort("_id", -1) 
    lista_registros = []
    for doc in registros_db:
        doc["_id"] = str(doc["_id"])
        lista_registros.append(doc)
    return {"status": "success", "data": lista_registros}

@app.delete("/eliminar/{id_registro}")
async def eliminar_registro(id_registro: str):
    try:
        resultado = coleccion.delete_one({"_id": ObjectId(id_registro)})
        if resultado.deleted_count == 1:
            return {"status": "success", "message": "Registro eliminado"}
        return {"status": "error", "message": "No encontrado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)