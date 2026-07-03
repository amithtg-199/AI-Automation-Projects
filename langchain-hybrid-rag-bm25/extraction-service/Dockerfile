FROM python:3.12-slim

# Install system dependencies required for docling, unstructured, and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml main.py ./

RUN pip install --no-cache-dir uv && \
    uv pip install --system --index-url https://download.pytorch.org/whl/cpu torch torchvision && \
    uv pip install --system .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
