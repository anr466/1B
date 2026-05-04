FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# نظام deps منفصل لتحسين cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt ./
RUN pip install --upgrade pip && pip install -r requirements-prod.txt

# نسخ الكود فقط (بدون .venv, .agents, logs, flutter, إلخ)
COPY backend/ ./backend/
COPY bin/ ./bin/
COPY database/ ./database/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY start_server.py ./
COPY setup.sh ./

RUN mkdir -p logs backups tmp

EXPOSE 3002

CMD ["python", "start_server.py"]
