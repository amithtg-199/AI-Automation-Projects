FROM python:3.11-slim

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY init/ init/
COPY scripts/ scripts/

RUN pip install --no-cache-dir uv && \
    uv pip install --system --index-url https://download.pytorch.org/whl/cpu torch torchvision && \
    uv pip install --system .

COPY . .

EXPOSE 5679

CMD ["python", "init/main.py"]
