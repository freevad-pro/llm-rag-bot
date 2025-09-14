#!/bin/bash
# Остановка production приложения
# Использование: ./scripts/prod_stop.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

echo "🛑 Остановка ИИ-бота..."

# Переходим в рабочую директорию
cd /opt/llm-bot/app

# Проверяем текущий статус
log "📊 Текущий статус контейнеров:"
docker-compose -f docker-compose.prod.yml ps

# Останавливаем контейнеры
log "🛑 Останавливаем контейнеры..."
docker-compose -f docker-compose.prod.yml down

# Проверяем что все остановлено
log "🔍 Проверяем что контейнеры остановлены..."
RUNNING=$(docker ps --filter "name=app-" --format "table {{.Names}}" | wc -l)

if [ $RUNNING -eq 1 ]; then  # 1 потому что wc считает заголовок
    success "Все контейнеры остановлены"
else
    error "Некоторые контейнеры все еще работают:"
    docker ps --filter "name=app-"
    
    echo
    echo "Для принудительной остановки выполните:"
    echo "docker stop \$(docker ps -q --filter \"name=app-\")"
fi

success "🎯 Остановка завершена!"
