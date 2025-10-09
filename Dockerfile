FROM python:3.12-slim-trixie

# Копируем uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Копирование файлов проекта
COPY pyproject.toml ./
COPY main.py ./
COPY app ./app

# Создание директории для логов
RUN mkdir -p /app/logs

# Синхронизация зависимостей через uv
RUN uv sync

# Открытие порта
EXPOSE 8000

# Команда запуска
CMD ["uv", "run", "main.py"]
