# ==============================================================================
# Production Dockerfile for LabelCheck Backend (FastAPI + Tesseract OCR + OpenCV)
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install native system dependencies:
# - tesseract-ocr & tesseract-ocr-eng: OCR text extraction
# - libgl1 & libglib2.0-0: OpenCV headless dependencies
# - curl: Healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies first for caching layers
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend /app

# Ensure data directories exist
RUN mkdir -p /app/data/uploads /app/data/preprocessed /app/data/reports /app/data/samples

# Default port
ENV PORT=8001 \
    HOST=0.0.0.0 \
    DATA_DIR=/app/data

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch production server with dynamic port support
CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
