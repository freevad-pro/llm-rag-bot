#!/bin/bash
# Простая проверка PostgreSQL для development окружения
# Использование: ./scripts/check_postgres_dev.sh

echo "🔍 Проверка PostgreSQL в development режиме"
echo

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Файл docker-compose.yml не найден"
    echo "Запустите скрипт из корневой директории проекта"
    exit 1
fi

echo "📁 Используется: Development (docker-compose.yml)"
echo

# Прямая проверка подключения
echo "🔗 Проверяем подключение к PostgreSQL..."
if docker-compose exec postgres pg_isready -U postgres -q 2>/dev/null; then
    echo "✅ PostgreSQL готов к подключениям"
else
    echo "❌ PostgreSQL не готов"
    echo "Запустите: docker-compose up -d postgres"
    exit 1
fi

# Проверяем подключение к базе
echo "🗄️  Проверяем базу catalog_db..."
if docker-compose exec postgres psql -U postgres -d catalog_db -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Подключение к базе работает"
    
    # Показываем версию
    VERSION=$(docker-compose exec postgres psql -U postgres -d catalog_db -t -c "SELECT version();" 2>/dev/null | head -1 | xargs)
    if [ ! -z "$VERSION" ]; then
        echo "📋 $VERSION"
    fi
else
    echo "❌ Ошибка подключения к базе"
    echo "Проверьте пароль в docker-compose.yml"
    exit 1
fi

# Проверяем приложение
echo "🤖 Проверяем приложение..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Health check прошел"
else
    echo "⚠️  Приложение не отвечает или не запущено"
    echo "Запустите: docker-compose up -d app"
fi

echo
echo "🎉 Development окружение готово!"
echo
echo "💡 Полезные команды:"
echo "Подключиться к PostgreSQL:"
echo "  docker-compose exec postgres psql -U postgres -d catalog_db"
echo "Перезапустить все:"
echo "  docker-compose restart"
echo "Посмотреть логи:"
echo "  docker-compose logs -f"
