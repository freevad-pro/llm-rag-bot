#!/bin/bash
# Просмотр логов production приложения
# Использование: 
#   ./scripts/prod_logs.sh          - все логи в реальном времени
#   ./scripts/prod_logs.sh app      - только логи приложения  
#   ./scripts/prod_logs.sh bot      - только логи телеграм бота
#   ./scripts/prod_logs.sh postgres - только логи базы данных

set -e

# Цвета для вывода
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

# Переходим в рабочую директорию
cd /opt/llm-bot/app

SERVICE=${1:-""}

if [ -z "$SERVICE" ]; then
    echo "📋 Показываем логи всех сервисов в реальном времени..."
    echo "Для выхода нажмите Ctrl+C"
    echo
    docker-compose -f docker-compose.prod.yml logs -f
elif [ "$SERVICE" = "app" ] || [ "$SERVICE" = "bot" ] || [ "$SERVICE" = "postgres" ]; then
    echo "📋 Показываем логи сервиса '$SERVICE' в реальном времени..."
    echo "Для выхода нажмите Ctrl+C"
    echo
    docker-compose -f docker-compose.prod.yml logs -f $SERVICE
else
    echo "❌ Неизвестный сервис: $SERVICE"
    echo
    echo "Доступные сервисы:"
    echo "  app      - веб-приложение"
    echo "  bot      - телеграм бот"
    echo "  postgres - база данных"
    echo
    echo "Использование:"
    echo "  $0          - все логи"
    echo "  $0 app      - только app" 
    echo "  $0 bot      - только bot"
    echo "  $0 postgres - только postgres"
    exit 1
fi
