FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN pip install poetry

# Настройка Poetry
RUN poetry config virtualenvs.create false

# Копирование файлов зависимостей
COPY pyproject.toml README.md ./

# Установка зависимостей без установки проекта
RUN poetry install --only=main --no-interaction --no-ansi --no-root

# Копирование исходного кода
COPY . .

# Создание директорий для данных
RUN mkdir -p /app/data/chroma /app/data/uploads

# Expose порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
