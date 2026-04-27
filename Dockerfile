FROM python:3.10-slim

# Evitamos preguntas interactivas
ENV DEBIAN_FRONTEND=noninteractive

# Cambiamos libgl1-mesa-glx por libgl1 que es la version actual
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "api_kyc:app", "--host", "0.0.0.0", "--port", "8000"]