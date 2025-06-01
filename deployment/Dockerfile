# Используем официальный образ Python 3.13
FROM python:3.13-slim-bookworm

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
RUN pip install --no-cache-dir uv

# Установка рабочей директории
WORKDIR /app

# Копирование только файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей с помощью uv
RUN uv pip install --no-cache -e .

# Копирование исходного кода приложения
COPY src/ ./src
COPY tests/ ./tests

# Установка переменных окружения
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV GRPC_DNS_RESOLVER=native

# Установка модели spaCy
RUN python -m spacy download ru_core_news_md

# Открываем порт для FastAPI
EXPOSE 8000

# Команда запуска приложения
CMD ["scientia-app"]