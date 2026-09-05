# Lightweight production image for Render Free (0.1 CPU / 512 MB RAM)
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TESSERACT_CMD=/usr/bin/tesseract

# Tesseract + Vietnamese/English language data. No compiler/toolchain is kept.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tesseract-ocr \
       tesseract-ocr-vie \
       tesseract-ocr-eng \
       libglib2.0-0 \
       libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install only runtime dependencies; opencv-headless avoids GUI/X11 packages.
COPY requirements-api.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt -r requirements.txt

COPY app ./app

# Hugging Face Spaces supplies PORT; default 7860 also works locally.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
