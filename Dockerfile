# Usamos una versión ligera de Python
FROM python:3.10-slim

# Instalamos Tesseract OCR y dependencias del sistema operativo
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    libglib2.0-0 \
    && apt-get clean

# Creamos la carpeta de trabajo en la nube
WORKDIR /app

# Copiamos todos tus archivos (api_kyc.py, best.pt, etc.) a la nube
COPY . .

# Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para encender tu API en la nube
CMD ["uvicorn", "api_kyc:app", "--host", "0.0.0.0", "--port", "8000"]