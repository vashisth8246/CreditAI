FROM node:24-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/index.html frontend/vite.config.ts frontend/tsconfig.json ./
COPY frontend/tsconfig.app.json frontend/tsconfig.node.json ./
COPY frontend/src/ ./src/
COPY frontend/public/ ./public/
RUN npm run build

FROM python:3.11-slim AS python-dependencies

WORKDIR /build
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --home-dir /home/creditai creditai \
    && mkdir -p /tmp/matplotlib \
    && chown creditai:creditai /tmp/matplotlib

COPY --from=python-dependencies /install /usr/local
COPY requirements.txt ./requirements.txt
COPY src/ ./src/
COPY models/ ./models/
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

USER creditai
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '10000') + '/health', timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
