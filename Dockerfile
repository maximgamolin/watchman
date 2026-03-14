# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Зависимости для сборки psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime-зависимости libpq (нужна psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты из builder
COPY --from=builder /install /usr/local

# Копируем исходный код
COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
