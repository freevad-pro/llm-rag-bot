#!/bin/bash
# Обновление ИИ-бота с сохранением локальных изменений в stash
# Использование: ./scripts/update_stash.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[STASH UPDATE]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo "💾 Обновление ИИ-бота с сохранением локальных изменений..."
echo "Локальные изменения будут сохранены в Git stash"
echo

log "Запускаем основной скрипт обновления..."
exec /opt/llm-bot/scripts/update.sh --force

success "Обновление с сохранением изменений завершено!"
echo
warning "Ваши локальные изменения сохранены в Git stash."
warning "Для их восстановления используйте: git stash pop"
