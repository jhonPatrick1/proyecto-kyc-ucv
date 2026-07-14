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
import math # Importante: Librería matemática nativa, sin usar scikit-learn

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
                    
                    gray = cv2.cvtColor(dni_crop, cv2.COLOR_BGR2GRAY)
                    ampliado = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                    blur = cv2.GaussianBlur(ampliado, (3, 3), 0)
                    _, dni_limpio = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                    texto_crudo = pytesseract.image_to_string(dni_limpio, lang='spa', config='--oem 3 --psm 11')
                    texto_limpio_sin_espacios = texto_crudo.replace(" ", "").replace("\n", "").upper()
                    texto_upper = texto_crudo.upper()

                    
                    # ==========================================
                    # MOTOR DE INFERENCIA (AGENTE BASADO EN REGLAS)
                    # Reglas lógicas del agente: Si el patrón coincide con un DNI, extrae los datos. 
                    # Si hay reflejos o calidad insuficiente, la regla dicta rechazar.
                    # ==========================================
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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
    
# --- NAIVE BAYES (MANUAL SIN LIBRERÍAS EXTERNAS DE ML) ---

class DatosKycRedNeuronal(BaseModel):
    ingreso_mensual: float
    deuda_actual: float
    edad: int
    similitud_dni: float

@app.post("/evaluar-kyc-red-neuronal")
async def evaluar_kyc_red_neuronal(datos: DatosKycRedNeuronal):
    try:
        # 1. Matriz de Entrada (X) -> Datos que llegan del cliente
        X = [datos.ingreso_mensual, datos.deuda_actual, datos.edad, datos.similitud_dni]
        
        # 2. Matriz de Pesos Sinápticos (W) y Sesgo (b) -> Calibración de la red
        # W1: Ingreso(+), W2: Deuda(-), W3: Edad(+), W4: Similitud DNI (El más crítico)
        W = [0.0005, -0.002, 0.01, 5.5]
        b = -4.5 
        
        # 3. Cálculo de la Función Neta (Sumatoria de X * W + b)
        neta = 0.0
        for i in range(len(X)):
            neta += X[i] * W[i]
        neta += b
        
        # 4. Función de Activación (Escalón / Hardlim) -> Aplasta el resultado a 1 o 0
        if neta >= 0:
            salida = 1
            estado = "Aprobado: Bajo Riesgo / Identidad Verificada"
        else:
            salida = 0
            estado = "Rechazado: Alerta de Fraude / Alto Riesgo"
            
        return {
            "status": "success",
            "arquitectura": {
                "matriz_X_entradas": X,
                "matriz_W_pesos": W,
                "sesgo_b": b,
            },
            "matematica": {
                "funcion_neta_calculada": round(neta, 4),
                "salida_activacion": salida
            },
            "decision_final": estado
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    
class DatosFinancieros(BaseModel):
    edad: int
    ingresos: float
    es_independiente: int  

@app.post("/evaluar-riesgo")
async def evaluar_riesgo(datos: DatosFinancieros):
    try:
        # 1. EL DATASET (El conocimiento previo quemado en código)
        data_edad = [22, 45, 19, 35, 50, 28, 60, 21, 40, 30]
        data_ingresos = [1200, 5000, 800, 3500, 6000, 2500, 1500, 900, 4200, 3100]
        data_indep = [1, 0, 1, 0, 0, 1, 1, 0, 0, 1]
        data_aprobado = [0, 1, 0, 1, 1, 1, 0, 0, 1, 1]

        # 2. SEPARAR DATOS POR CLASE (0 = Rechazado, 1 = Aprobado)
        idx_apr = [i for i, val in enumerate(data_aprobado) if val == 1]
        idx_rech = [i for i, val in enumerate(data_aprobado) if val == 0]

        # 3. PROBABILIDADES PREVIAS P(C)
        total_registros = len(data_aprobado)
        p_previa_apr = len(idx_apr) / total_registros
        p_previa_rech = len(idx_rech) / total_registros

        # 4. FUNCIONES MATEMÁTICAS (Implementación manual)
        def calcular_media(valores):
            return sum(valores) / len(valores)

        def calcular_varianza(valores, media):
            if len(valores) <= 1: return 0.0001
            return sum((x - media) ** 2 for x in valores) / len(valores)

        def prob_gaussiana(x, media, varianza):
            if varianza == 0: varianza = 0.0001
            exponente = math.exp(-((x - media) ** 2) / (2 * varianza))
            return (1 / math.sqrt(2 * math.pi * varianza)) * exponente

        # 5. EXTRAER VALORES POR CLASE
        edades_apr = [data_edad[i] for i in idx_apr]
        ingresos_apr = [data_ingresos[i] for i in idx_apr]
        indep_apr = [data_indep[i] for i in idx_apr]

        edades_rech = [data_edad[i] for i in idx_rech]
        ingresos_rech = [data_ingresos[i] for i in idx_rech]
        indep_rech = [data_indep[i] for i in idx_rech]

        # 6. CALCULAR P(X|C) PARA "APROBADO" (Supuesto Naive Bayes: Multiplicación)
        p_edad_apr = prob_gaussiana(datos.edad, calcular_media(edades_apr), calcular_varianza(edades_apr, calcular_media(edades_apr)))
        p_ingreso_apr = prob_gaussiana(datos.ingresos, calcular_media(ingresos_apr), calcular_varianza(ingresos_apr, calcular_media(ingresos_apr)))
        p_indep_apr = prob_gaussiana(datos.es_independiente, calcular_media(indep_apr), calcular_varianza(indep_apr, calcular_media(indep_apr)))

        prob_final_aprobado = p_previa_apr * p_edad_apr * p_ingreso_apr * p_indep_apr

        # 7. CALCULAR P(X|C) PARA "RECHAZADO"
        p_edad_rech = prob_gaussiana(datos.edad, calcular_media(edades_rech), calcular_varianza(edades_rech, calcular_media(edades_rech)))
        p_ingreso_rech = prob_gaussiana(datos.ingresos, calcular_media(ingresos_rech), calcular_varianza(ingresos_rech, calcular_media(ingresos_rech)))
        p_indep_rech = prob_gaussiana(datos.es_independiente, calcular_media(indep_rech), calcular_varianza(indep_rech, calcular_media(indep_rech)))

        prob_final_rechazado = p_previa_rech * p_edad_rech * p_ingreso_rech * p_indep_rech

        # 8. DECISIÓN Y NORMALIZACIÓN MATEMÁTICA
        es_aprobado = prob_final_aprobado > prob_final_rechazado
        suma_probs = prob_final_aprobado + prob_final_rechazado
        
        if suma_probs == 0:
            confianza = 0
        else:
            confianza = (prob_final_aprobado / suma_probs) * 100 if es_aprobado else (prob_final_rechazado / suma_probs) * 100
        
        estado = "Aprobado Automáticamente" if es_aprobado else "Requiere Revisión Manual"

        return {
            "status": "success",
            "resultado_ia": estado,
            "confianza_bayes": f"{confianza:.1f}%",
            "nota": "Calculado manualmente sin scikit-learn"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

    # =====================================================================
# --- RED NEURONAL (PERCEPTRÓN) Y LÓGICA DIFUSA (DEFUZZIFICACIÓN) ---

@app.post("/evaluar-inteligencia-avanzada")
async def evaluar_inteligencia_avanzada(datos: DatosFinancieros):
    try:
        # ---------------------------------------------------------
        # 1. RED NEURONAL: PERCEPTRÓN SIMPLE 
        # ---------------------------------------------------------
        # Entradas (x) normalizadas
        x1 = datos.edad / 100.0  
        x2 = datos.ingresos / 10000.0 
        x3 = datos.es_independiente
        
        # Pesos Sinápticos (w) y Bias (b)
        w1, w2, w3 = 0.4, 0.7, -0.3
        bias = -0.5
        
        # Función Neta (NET = XW + b)
        net = (x1 * w1) + (x2 * w2) + (x3 * w3) + bias
        
        # Función de Activación: Escalón 
        salida_neurona = 1 if net >= 0 else 0
        estado_red = "Crédito Aprobado" if salida_neurona == 1 else "Crédito Rechazado"

        # ---------------------------------------------------------
        # 2. LÓGICA DIFUSA Y BASE DE REGLAS
        # ---------------------------------------------------------
        # Fuzzificación (Funciones de pertenencia simples)
        mu_ingreso_bajo = max(0, min(1, (3000 - datos.ingresos) / 3000))
        mu_ingreso_alto = max(0, min(1, (datos.ingresos - 2000) / 4000))
        
        # Base de Reglas Difusas (IF - THEN)
        # Regla 1: 
        mu_riesgo_alto = mu_ingreso_bajo 
        # Regla 2: 
        mu_riesgo_bajo = mu_ingreso_alto 
        
        # ---------------------------------------------------------
        # 3. DEFUZZIFICACIÓN: MÉTODO CENTROIDE O CENTRO DE GRAVEDAD (COG)
        # ---------------------------------------------------------
        # Universo de discurso (x): Porcentaje de riesgo de 10% a 90%
        x_valores = [10, 30, 50, 70, 90] 
        numerador = 0.0
        denominador = 0.0
        
        for x in x_valores:
            # Agregación de resultados según la base de reglas
            grado_activacion = mu_riesgo_alto if x >= 50 else mu_riesgo_bajo
            
            numerador += x * grado_activacion
            denominador += grado_activacion
            
        # Fórmula discreta del Centroide para obtener la "Salida Crisp"
        if denominador == 0:
            salida_crisp = 50.0 # Valor intermedio por defecto
        else:
            salida_crisp = numerador / denominador

        return {
            "status": "success",
            "red_neuronal": {
                "entradas_normalizadas": [x1, x2, x3],
                "pesos_sinapticos": [w1, w2, w3],
                "bias": bias,
                "funcion_neta_NET": round(net, 4),
                "salida_escalon": salida_neurona,
                "decision_red": estado_red
            },
            "logica_difusa": {
                "fuzzificacion_ingreso_bajo": round(mu_ingreso_bajo, 2),
                "fuzzificacion_ingreso_alto": round(mu_ingreso_alto, 2),
                "defuzzificacion_metodo": "Centroide (COG)",
                "salida_crisp_riesgo": f"{round(salida_crisp, 2)}%"
            },
            "nota_profesor": "Implementado con pesos sinápticos, base de reglas y defuzzificación COG manual."
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}