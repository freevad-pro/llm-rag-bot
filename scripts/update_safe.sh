#!/bin/bash
# Безопасное обновление ИИ-бота (остановится при локальных изменениях)
# Использование: ./scripts/update_safe.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[SAFE UPDATE]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo "🛡️ Безопасное обновление ИИ-бота..."
echo "Остановится при обнаружении локальных изменений"
echo

log "Запускаем основной скрипт обновления..."
exec /opt/llm-bot/scripts/update.sh

success "Безопасное обновление завершено!"
