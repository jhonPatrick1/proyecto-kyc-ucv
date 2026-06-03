FROM python:3.10-slim

# Evitamos preguntas interactivas
ENV DEBIAN_FRONTEND=noninteractive

# Instalamos Tesseract (con el paquete en español que agregaste) y OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiamos primero las dependencias para que instale más rápido
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el resto (tu código de Python y el best.pt)
COPY . .

# HUGGING FACE EXIGE EL PUERTO 7860
EXPOSE 7860

CMD ["uvicorn", "api_kyc:app", "--host", "0.0.0.0", "--port", "7860"]