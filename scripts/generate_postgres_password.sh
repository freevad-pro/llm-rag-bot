#!/bin/bash
# Скрипт генерации безопасного пароля для PostgreSQL
# Использование: ./scripts/generate_postgres_password.sh

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Генератор паролей PostgreSQL для ИИ-бота${NC}"
echo

# Генерируем безопасный пароль
# Используем символы, безопасные для URL и bash
NEW_PASSWORD=$(openssl rand -base64 48 | tr -d "=+/\n" | head -c 32)

# Если openssl недоступен, используем альтернативный метод
if [ -z "$NEW_PASSWORD" ]; then
    NEW_PASSWORD=$(head /dev/urandom | tr -dc 'A-Za-z0-9' | head -c 32)
fi

echo -e "${GREEN}✅ Сгенерирован новый пароль:${NC}"
echo -e "${YELLOW}$NEW_PASSWORD${NC}"
echo

echo -e "${BLUE}📝 Для применения в production добавьте в /opt/llm-bot/config/.env:${NC}"
echo
echo "POSTGRES_PASSWORD=$NEW_PASSWORD"
echo "DATABASE_URL=postgresql+asyncpg://postgres:$NEW_PASSWORD@postgres:5432/catalog_db"
echo

echo -e "${BLUE}🔧 Команды для применения пароля:${NC}"
echo "1. Остановить сервисы:"
echo "   cd /opt/llm-bot/app && docker-compose -f docker-compose.prod.yml down"
echo
echo "2. Отредактировать конфигурацию:"
echo "   nano /opt/llm-bot/config/.env"
echo
echo "3. Запустить с новым паролем:"
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo

echo -e "${YELLOW}⚠️  Сохраните пароль в безопасном месте!${NC}"
