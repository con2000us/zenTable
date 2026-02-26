FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OCR_HOST=0.0.0.0 \
    OCR_PORT=8000 \
    OCR_LANG=ch \
    USE_ANGLE_CLS=true

WORKDIR /app

# System deps for Pillow/OpenCV/PaddleOCR runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements-ocr.txt /app/requirements-ocr.txt
RUN pip install --upgrade pip && pip install -r /app/requirements-ocr.txt

# Copy service code
COPY api /app/api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "api.paddleocr_service:app", "--host", "0.0.0.0", "--port", "8000"]
