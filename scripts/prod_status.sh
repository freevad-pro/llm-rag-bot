#!/bin/bash
# Проверка статуса production приложения
# Использование: ./scripts/prod_status.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo "📊 Статус ИИ-бота в production..."

# Переходим в рабочую директорию
cd /opt/llm-bot/app

echo
echo "=== DOCKER КОНТЕЙНЕРЫ ==="
docker-compose -f docker-compose.prod.yml ps

echo
echo "=== ИСПОЛЬЗОВАНИЕ РЕСУРСОВ ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker-compose -f docker-compose.prod.yml ps -q) 2>/dev/null || echo "Контейнеры не запущены"

echo
echo "=== ПРОВЕРКА ДОСТУПНОСТИ ==="

# Проверка health endpoint
log "🔍 Проверка health endpoint..."
if curl -s http://localhost:8000/health > /dev/null; then
    HEALTH_DATA=$(curl -s http://localhost:8000/health)
    success "Health endpoint доступен"
    echo "$HEALTH_DATA" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_DATA"
else
    error "Health endpoint недоступен"
fi

echo
echo "=== ПРОВЕРКА ПОРТОВ ==="
log "🔍 Открытые порты..."
ss -tlnp | grep ":8000" && success "Порт 8000 открыт" || warning "Порт 8000 не найден"

echo
echo "=== ЛОГИ (последние 5 строк) ==="
echo "--- APP ---"
docker-compose -f docker-compose.prod.yml logs app 2>/dev/null | tail -5 || echo "Логи app недоступны"

echo "--- BOT ---" 
docker-compose -f docker-compose.prod.yml logs bot 2>/dev/null | tail -5 || echo "Логи bot недоступны"

echo "--- POSTGRES ---"
docker-compose -f docker-compose.prod.yml logs postgres 2>/dev/null | tail -5 || echo "Логи postgres недоступны"

echo
echo "=== ДИСКОВОЕ ПРОСТРАНСТВО ==="
log "💾 Использование диска в /opt/llm-bot..."
du -sh /opt/llm-bot/* 2>/dev/null || warning "Не удается получить информацию о диске"

echo
echo "=== КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ ==="
echo "Запуск:      /opt/llm-bot/scripts/start_production.sh"
echo "Перезапуск:  /opt/llm-bot/scripts/prod_restart.sh"  
echo "Остановка:   /opt/llm-bot/scripts/prod_stop.sh"
echo "Обновление:  /opt/llm-bot/scripts/update.sh"
echo "Логи:        docker-compose -f /opt/llm-bot/app/docker-compose.prod.yml logs -f"

success "📋 Проверка статуса завершена!"
