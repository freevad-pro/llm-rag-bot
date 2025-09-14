#!/bin/bash
# Принудительное обновление ИИ-бота с перезаписью локальных изменений
# Использование: ./scripts/update_force.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[FORCE UPDATE]${NC} $1"
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

echo "🔨 ПРИНУДИТЕЛЬНОЕ обновление ИИ-бота..."
echo -e "${RED}ВНИМАНИЕ: Все локальные изменения будут ПЕРЕЗАПИСАНЫ!${NC}"
echo

# Запрашиваем подтверждение
read -p "Вы уверены? Все несохраненные изменения будут потеряны! (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Операция отменена пользователем."
    exit 0
fi

warning "⚠️  Последнее предупреждение! Локальные изменения будут удалены через 5 секунд..."
for i in 5 4 3 2 1; do
    echo -n "$i... "
    sleep 1
done
echo

log "Запускаем принудительное обновление..."
exec /opt/llm-bot/scripts/update.sh --force-overwrite

success "Принудительное обновление завершено!"
