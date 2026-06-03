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
import gc 
from pydantic import BaseModel
import pandas as pd
from sklearn.naive_bayes import GaussianNB

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
    try:
        request_object_content = await file.read()
        img = Image.open(io.BytesIO(request_object_content))
        
        img = ImageOps.exif_transpose(img)
        
        # Mantenemos 1280 para aprovechar los 16GB de RAM de Hugging Face
        img.thumbnail((1280, 1280)) 
        
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        results = model(frame, conf=0.5, verbose=False)
        
        dni_final = "No detectado"
        texto_limpio_exitoso = ""
        
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
                
                for rot in rotaciones:
                    if rot is not None:
                        dni_crop = cv2.rotate(dni_crop_original, rot)
                    else:
                        dni_crop = dni_crop_original
                    
                    # --- PROCESAMIENTO LIMPIO PARA ALTA RESOLUCIÓN ---
                    # Eliminamos los filtros agresivos. Solo pasamos la imagen a escala de grises.
                    # Tesseract 4+ hace su propia binarización interna y lee mejor los fondos con marcas de agua así.
                    gray = cv2.cvtColor(dni_crop, cv2.COLOR_BGR2GRAY)
                    
                    texto_crudo = pytesseract.image_to_string(gray, lang='spa', config='--oem 3 --psm 11')
                    texto_limpio_sin_espacios = texto_crudo.replace(" ", "").replace("\n", "").upper()
                    texto_upper = texto_crudo.upper()

                    print(f"👀 OCR LEYÓ: {texto_limpio_sin_espacios}")

                    match_frontal = re.search(r'P[EF]R[.\-\s]*([0-9O]{8})', texto_upper)
                    match_rojo = re.search(r'D[N\\][I1L][.\-\s]*([0-9O]{8})', texto_upper)
                    match_trasera = re.search(r'([0-9O]{8})[<CKE(]+(\d)', texto_limpio_sin_espacios)
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
                
                if dni_final != "No detectado":
                    break
        
        if dni_final == "No detectado":
            return {"status": "error", "message": "No se detectó un DNI válido o legible"}

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
            else:
                verificacion = f"Bloqueo API: {response.status_code}"
        except Exception as e:
            verificacion = "Timeout o caída de API"

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
        
    finally:
        gc.collect()

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
    
    # --- NAIVE BAYES ---


class DatosFinancieros(BaseModel):
    edad: int
    ingresos: float
    es_independiente: int  

@app.post("/evaluar-riesgo")
async def evaluar_riesgo(datos: DatosFinancieros):
    try:
        # 1. EL DATASET (El conocimiento previo)
        # Aquí le enseñamos a la IA con casos pasados para que calcule la probabilidad.
        # 1 = Aprobado, 0 = Rechazado
        data = {
            'edad': [22, 45, 19, 35, 50, 28, 60, 21, 40, 30],
            'ingresos': [1200, 5000, 800, 3500, 6000, 2500, 1500, 900, 4200, 3100],
            'es_independiente': [1, 0, 1, 0, 0, 1, 1, 0, 0, 1],
            'aprobado': [0, 1, 0, 1, 1, 1, 0, 0, 1, 1]
        }
        df = pd.DataFrame(data)
        
        # Separamos las características (X) y lo que queremos predecir (y)
        X = df[['edad', 'ingresos', 'es_independiente']]
        y = df['aprobado']

        # 2. ENTRENAMIENTO DEL MODELO NAIVE BAYES
        modelo = GaussianNB()
        modelo.fit(X, y)

        # 3. PREDICCIÓN PARA EL NUEVO USUARIO ESCANEADO
        nuevo_cliente = pd.DataFrame(
            [[datos.edad, datos.ingresos, datos.es_independiente]],
            columns=['edad', 'ingresos', 'es_independiente']
        )
        
        # Aplicamos el teorema de Bayes para predecir
        prediccion = modelo.predict(nuevo_cliente)[0]
        # Obtenemos el porcentaje de seguridad matemática de la decisión
        probabilidad = modelo.predict_proba(nuevo_cliente)[0][1] * 100

        estado = "Aprobado Automáticamente" if prediccion == 1 else "Requiere Revisión Manual"
        
        return {
            "status": "success",
            "resultado_ia": estado, 
            "confianza_bayes": f"{probabilidad:.1f}%"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}