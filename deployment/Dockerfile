FROM python:3.13-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y postgresql-client


# Установка uv
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml ./

# Установка зависимостей с помощью uv
RUN uv pip install --system --no-cache -e .

COPY src/ ./src
COPY tests/ ./tests

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV GRPC_DNS_RESOLVER=native

RUN python -m spacy download ru_core_news_md

COPY deployment/wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

EXPOSE 8000

CMD ["/wait-for-db.sh", "db", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

