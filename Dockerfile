FROM python:3.12-slim

ENV PYTHONUNBUFFRED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils

COPY requirements.txt .

RUN pip install --no-cache -r requirements.txt

COPY . .

CMD ["uvicorn", "src.main:app"]