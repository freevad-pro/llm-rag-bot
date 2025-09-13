#!/bin/bash
# Скрипт проверки подключения к PostgreSQL
# Использование: ./scripts/check_postgres_connection.sh

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Проверка подключения к PostgreSQL${NC}"
echo

# Определяем путь к docker-compose файлу
if [ -f "/opt/llm-bot/app/docker-compose.prod.yml" ] && [ -f "/opt/llm-bot/config/.env" ]; then
    COMPOSE_FILE="/opt/llm-bot/app/docker-compose.prod.yml"
    ENV_TYPE="Production"
elif [ -f "docker-compose.prod.yml" ] && [ -f "/opt/llm-bot/config/.env" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_TYPE="Production"
elif [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
    ENV_TYPE="Development"
else
    echo -e "${RED}❌ Docker Compose файл не найден${NC}"
    echo "Доступные варианты:"
    echo "- Development: docker-compose.yml"
    echo "- Production: docker-compose.prod.yml + /opt/llm-bot/config/.env"
    exit 1
fi

echo -e "${BLUE}📁 Используется: $ENV_TYPE ($COMPOSE_FILE)${NC}"
echo

# Проверяем готовность PostgreSQL напрямую
echo -e "${BLUE}🔗 Проверяем подключение к PostgreSQL...${NC}"
if docker-compose -f $COMPOSE_FILE exec postgres pg_isready -U postgres -q 2>/dev/null; then
    echo -e "${GREEN}✅ PostgreSQL запущен и готов к подключениям${NC}"
else
    echo -e "${RED}❌ PostgreSQL не готов к подключениям${NC}"
    echo "Подождите несколько секунд и попробуйте снова"
    exit 1
fi

# Проверяем подключение к базе данных
echo -e "${BLUE}🗄️  Проверяем подключение к базе catalog_db...${NC}"
if docker-compose -f $COMPOSE_FILE exec postgres psql -U postgres -d catalog_db -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Подключение к базе данных работает${NC}"
    
    # Показываем версию PostgreSQL
    VERSION=$(docker-compose -f $COMPOSE_FILE exec postgres psql -U postgres -d catalog_db -t -c "SELECT version();" | head -1 | xargs)
    echo -e "${BLUE}📋 Версия: $VERSION${NC}"
    
else
    echo -e "${RED}❌ Ошибка подключения к базе данных${NC}"
    echo
    echo -e "${YELLOW}🔧 Возможные причины:${NC}"
    echo "1. Неверный пароль в конфигурации"
    echo "2. База данных еще не создана"
    echo "3. Проблемы с правами доступа"
    echo
    echo -e "${BLUE}📝 Проверьте настройки в:${NC}"
    if [ "$ENV_TYPE" = "Production" ]; then
        echo "- /opt/llm-bot/config/.env"
    else
        echo "- .env файл (если используется)"
        echo "- docker-compose.yml"
    fi
    exit 1
fi

# Проверяем подключение приложения (если запущено)
echo -e "${BLUE}🤖 Проверяем подключение приложения...${NC}"
if docker-compose -f $COMPOSE_FILE ps app | grep -q "Up"; then
    echo -e "${GREEN}✅ Контейнер приложения запущен${NC}"
    
    # Проверяем health endpoint
    sleep 2
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check приложения прошел${NC}"
    else
        echo -e "${YELLOW}⚠️  Health check приложения не прошел${NC}"
        echo "Проверьте логи: docker-compose -f $COMPOSE_FILE logs app"
    fi
else
    echo -e "${YELLOW}⚠️  Контейнер приложения не запущен${NC}"
fi

# Показываем статистику базы данных
echo
echo -e "${BLUE}📊 Статистика базы данных:${NC}"
TABLES_COUNT=$(docker-compose -f $COMPOSE_FILE exec postgres psql -U postgres -d catalog_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
DB_SIZE=$(docker-compose -f $COMPOSE_FILE exec postgres psql -U postgres -d catalog_db -t -c "SELECT pg_size_pretty(pg_database_size('catalog_db'));" 2>/dev/null | xargs)

if [ ! -z "$TABLES_COUNT" ]; then
    echo "- Количество таблиц: $TABLES_COUNT"
fi
if [ ! -z "$DB_SIZE" ]; then
    echo "- Размер базы данных: $DB_SIZE"
fi

echo
echo -e "${GREEN}🎉 Проверка завершена успешно!${NC}"

# Полезные команды
echo
echo -e "${BLUE}💡 Полезные команды:${NC}"
echo "Подключиться к PostgreSQL:"
echo "  docker-compose -f $COMPOSE_FILE exec postgres psql -U postgres -d catalog_db"
echo
echo "Посмотреть логи PostgreSQL:"
echo "  docker-compose -f $COMPOSE_FILE logs postgres"
echo
echo "Посмотреть логи приложения:"
echo "  docker-compose -f $COMPOSE_FILE logs app"
