FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OCR_HOST=0.0.0.0 \
    OCR_PORT=8010 \
    OCR_LANG=ch

WORKDIR /app

# Faster apt mirror (optional)
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      --extra-index-url https://pypi.org/simple \
      --default-timeout=120 \
      --retries=20

COPY api/paddle_table_service.py /app/api/paddle_table_service.py

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8010/health || exit 1

CMD ["python", "-m", "api.paddle_table_service"]
