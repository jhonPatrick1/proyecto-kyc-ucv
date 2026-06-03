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
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = "mongodb+srv://jhonpatrickcg_db_user:yHK7MkFlLeULjC23@cluster0.tknyeco.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["zindex_kyc_db"] 
coleccion = db["registros_dni"] 

model = YOLO("best.pt")

@app.post("/escanear")
async def escanear_dni(file: UploadFile = File(...)):
    request_object_content = await file.read()
    img = Image.open(io.BytesIO(request_object_content))
    
    img = ImageOps.exif_transpose(img)
    img.thumbnail((800, 800))
    
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    results = model(frame, conf=0.5, verbose=False)
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            dni_crop_original = frame[y1:y2, x1:x2]
            
            rotaciones = [
                None, 
                cv2.ROTATE_90_CLOCKWISE, 
                cv2.ROTATE_180, 
                cv2.ROTATE_90_COUNTERCLOCKWISE 
            ]
            
            dni_final = "No detectado"
            texto_limpio_exitoso = ""

            for rot in rotaciones:
                if rot is not None:
                    dni_crop = cv2.rotate(dni_crop_original, rot)
                else:
                    dni_crop = dni_crop_original
                
                # --- INICIO DE LA MEJORA DE IMAGEN ---
                gray = cv2.cvtColor(dni_crop, cv2.COLOR_BGR2GRAY)
                ampliado = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                
                # Filtros avanzados para eliminar reflejos y sombras
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                contraste = clahe.apply(ampliado)
                
                suavizado = cv2.bilateralFilter(contraste, 9, 75, 75)
                dni_limpio = cv2.adaptiveThreshold(suavizado, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                # --- FIN DE LA MEJORA DE IMAGEN ---

                # --- OCR Y BÚSQUEDA (REGEX) OPTIMIZADOS ---
                texto_crudo = pytesseract.image_to_string(dni_limpio, lang='spa', config='--oem 3 --psm 6')
                texto_limpio_sin_espacios = texto_crudo.replace(" ", "").replace("\n", "").upper()
                texto_upper = texto_crudo.upper()

                match_frontal = re.search(r'P[EF]R[.\-\s]*([0-9O]{8})', texto_upper)
                match_rojo = re.search(r'D[N\\][I1L][.\-\s]*([0-9O]{8})', texto_upper)
                match_trasera = re.search(r'([0-9O]{8})[<CKE(]+(\d)', texto_limpio_sin_espacios)
                # Comodín salvavidas: busca cualquier bloque de 8 números
                match_generico = re.search(r'(?<!\d)([0-9O]{8})(?!\d)', texto_limpio_sin_espacios)

                texto_limpio = texto_limpio_sin_espacios

                if match_frontal:
                    dni_final = match_frontal.group(1).replace("O", "0")
                    texto_limpio_exitoso = texto_limpio
                    break 
                elif match_rojo:
                    dni_final = match_rojo.group(1).replace("O", "0")
                    texto_limpio_exitoso = texto_limpio
                    break
                elif match_trasera:
                    dni_final = match_trasera.group(1).replace("O", "0")
                    texto_limpio_exitoso = texto_limpio
                    break
                elif match_generico:
                    dni_final = match_generico.group(1).replace("O", "0")
                    texto_limpio_exitoso = texto_limpio
                    break
            
            if dni_final == "No detectado":
                continue

            nombres, apellidos, verificacion = "No detectado", "No detectado", "No verificado"

            try:
                headers = {
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            
                url_api = f"https://api.apis.net.pe/v1/dni?numero={dni_final}"
                response = requests.get(url_api, headers=headers, timeout=8)
            
                if response.status_code == 200:
                    data = response.json()
                    nombres = data.get("nombres", "No detectado")
                    apellidos = f"{data.get('apellidoPaterno', '')} {data.get('apellidoMaterno', '')}".strip()
                    verificacion = "Verificado por RENIEC"
                    print(f"🌟 API Exitosa en Nube: {nombres}")
                else:
                    verificacion = f"Bloqueo API: {response.status_code}"
                    print(f"❌ La API respondió con error: {response.status_code}")
            except Exception as e:
                verificacion = "Timeout o caída de API"
                print(f"❌ Error interno API: {e}")

            match_nacimiento = re.search(r'(\d{6})\d?([MF])', texto_limpio_exitoso)
            edad_final = "No calculada"
            
            if match_nacimiento:
                fecha_cruda = match_nacimiento.group(1) 
                genero_final = "Masculino" if match_nacimiento.group(2) == "M" else "Femenino"
                
                año_crudo = int(fecha_cruda[0:2])
                año_real = 1900 + año_crudo if año_crudo > 26 else 2000 + año_crudo
                fecha_nac_final = f"{fecha_cruda[4:6]}/{fecha_cruda[2:4]}/{año_real}"
                
                try:
                    fecha_obj = datetime.strptime(fecha_nac_final, "%d/%m/%Y")
                    hoy = datetime.now()
                    edad_num = hoy.year - fecha_obj.year - ((hoy.month, hoy.day) < (fecha_obj.month, fecha_obj.day))
                    edad_final = f"{edad_num} años"
                except Exception:
                    edad_final = "Error al calcular"
            else:
                fecha_nac_final, genero_final = "No detectado", "-"

            # Validación personalizada
            if nombres == "No detectado" or dni_final == "No detectado":
                return {
                    "status": "error", 
                    "message": "Calidad insuficiente. Por favor, evite los reflejos y encuadre bien el DNI."
                }

            documento = {
                "nombres": nombres,
                "apellidos": apellidos,
                "dni": dni_final,
                "fecha_nacimiento": fecha_nac_final,
                "edad": edad_final,
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

@app.put("/actualizar/{id_registro}")
async def actualizar_registro(id_registro: str, datos: dict):
    try:
        nueva_fecha = datos.get("fecha_nacimiento")
        if not nueva_fecha:
            return {"status": "error", "message": "Falta la fecha"}

        fecha_obj = datetime.strptime(nueva_fecha, "%d/%m/%Y")
        hoy = datetime.now()
        edad_num = hoy.year - fecha_obj.year - ((hoy.month, hoy.day) < (fecha_obj.month, fecha_obj.day))
        nueva_edad = f"{edad_num} años"

        resultado = coleccion.update_one(
            {"_id": ObjectId(id_registro)},
            {"$set": {"fecha_nacimiento": nueva_fecha, "edad": nueva_edad}}
        )
        
        if resultado.modified_count == 1:
            return {"status": "success", "nueva_edad": nueva_edad}
        return {"status": "error", "message": "No se encontraron cambios"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)