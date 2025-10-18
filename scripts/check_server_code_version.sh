#!/bin/bash
# Скрипт для проверки версии кода на сервере

echo "🔍 Проверка версии кода на сервере"
echo "=================================="
echo ""

# Проверяем файл lead_service.py
echo "📄 Проверяем src/application/telegram/services/lead_service.py"
echo ""

# Ищем использование Conversation.created_at в методе find_inactive_users
if grep -A 20 "async def find_inactive_users" src/application/telegram/services/lead_service.py | grep -q "Conversation.created_at"; then
    echo "✅ Код использует Conversation.created_at (ПРАВИЛЬНО)"
else
    echo "⚠️  Код НЕ использует Conversation.created_at"
fi

# Ищем использование Conversation.started_at
if grep -A 20 "async def find_inactive_users" src/application/telegram/services/lead_service.py | grep -q "Conversation.started_at"; then
    echo "❌ Код использует Conversation.started_at (НЕПРАВИЛЬНО - старая версия)"
else
    echo "✅ Код НЕ использует Conversation.started_at (правильно)"
fi

echo ""
echo "📄 Проверяем модель Conversation в src/infrastructure/database/models.py"
echo ""

# Проверяем модель Conversation
if grep -A 15 "class Conversation" src/infrastructure/database/models.py | grep -q "created_at = Column"; then
    echo "✅ Модель имеет поле created_at"
else
    echo "❌ Модель НЕ имеет поле created_at"
fi

if grep -A 15 "class Conversation" src/infrastructure/database/models.py | grep -q "started_at = Column"; then
    echo "❌ Модель имеет поле started_at (старая версия)"
else
    echo "✅ Модель НЕ имеет поле started_at (правильно)"
fi

echo ""
echo "=================================="
echo ""
echo "💡 Рекомендации:"
echo ""
echo "Если код правильный, но ошибка все равно есть:"
echo "1. Перезапустите контейнер: docker-compose restart web"
echo "2. Очистите Python кэш: docker-compose exec web find . -type d -name __pycache__ -exec rm -rf {} +"
echo "3. Пересоберите контейнер: docker-compose build web && docker-compose up -d web"
echo ""
echo "Если код старый:"
echo "1. Обновите код: git pull origin main"
echo "2. Перезапустите: docker-compose restart web"

