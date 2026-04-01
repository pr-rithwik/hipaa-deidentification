FROM python:3.11-slim

# tesseract for OCR on scanned pages
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# spacy model can't be pip installed directly
RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 7860

CMD ["python", "main.py"]