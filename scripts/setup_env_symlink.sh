#!/bin/bash
# Создание симлинка для .env файла
# Решает проблемы с абсолютными путями

cd /opt/llm-bot/app

# Удаляем старый симлинк если есть
rm -f .env

# Создаем симлинк на главный .env файл
ln -sf ../config/.env .env

echo "✅ Симлинк создан: .env -> ../config/.env"
echo "📝 Теперь в docker-compose.prod.yml можно использовать:"
echo "env_file:"
echo "  - .env"

ls -la .env
