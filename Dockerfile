FROM python:3.12-slim AS base

# System dependencies for PDF parsing (pdftotext) and OCR
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        build-essential \
        libpoppler-cpp-dev \
        pkg-config \
        ocrmypdf \
        poppler-utils \
        tesseract-ocr \
        curl \
        git && \
    rm -rf /var/lib/apt/lists/*

# Install uv (official binary)
ADD https://astral.sh/uv/0.7.8/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:/root/.cargo/bin:$PATH" \
    UV_CACHE_DIR=/tmp/uv-cache \
    PYTHONUNBUFFERED=1 \
    PORT=8501

WORKDIR /app

# Dependency install — copy manifests first for better layer caching
COPY pyproject.toml uv.lock README.md ./
RUN uv venv && uv sync --all-extras --frozen --no-install-project

# Application code
COPY webapp/ ./webapp
COPY dashboard/ ./dashboard
COPY entrypoint.py ./

# Railway/Render/etc inject $PORT at runtime; default to 8501 locally
EXPOSE 8501

CMD ["sh", "-c", "uv run uvicorn webapp.api:app --host 0.0.0.0 --port ${PORT:-8501} --proxy-headers --forwarded-allow-ips='*'"]
