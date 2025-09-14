#!/bin/bash
# Основной скрипт управления production ИИ-ботом
# Использование: ./scripts/prod.sh [команда]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Функции для вывода
log() {
    echo -e "${BLUE}[PROD]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

info() {
    echo -e "${CYAN}ℹ️${NC} $1"
}

# Показываем help если нет параметров
show_help() {
    echo -e "${CYAN}🤖 ИИ-бот Production Manager${NC}"
    echo
    echo "Использование: $0 [команда]"
    echo
    echo -e "${GREEN}Основные команды:${NC}"
    echo "  start     - Запустить приложение"
    echo "  stop      - Остановить приложение"  
    echo "  restart   - Перезапустить с пересборкой"
    echo "  status    - Показать статус всех сервисов"
    echo "  logs      - Показать логи в реальном времени"
    echo
    echo -e "${GREEN}Логи отдельных сервисов:${NC}"
    echo "  logs-app  - Логи веб-приложения"
    echo "  logs-bot  - Логи Telegram бота"
    echo "  logs-db   - Логи базы данных"
    echo
    echo -e "${GREEN}Обновление кода:${NC}"
    echo "  update         - Безопасное обновление (остановится при локальных изменениях)"
    echo "  update-stash   - Обновление с сохранением локальных изменений в stash"
    echo "  update-force   - Принудительное обновление с перезаписью локальных файлов"
    echo
    echo -e "${GREEN}Тестирование:${NC}"
    echo "  test           - Запустить все тесты"
    echo "  test-fast      - Запустить только быстрые тесты"
    echo "  test-coverage  - Запустить тесты с покрытием кода"
    echo
    echo -e "${GREEN}Smoke Tests (быстрые проверки):${NC}"
    echo "  smoke          - Все быстрые проверки системы (~30с)"
    echo "  smoke-db       - Проверка подключения к БД"
    echo "  smoke-llm      - Проверка LLM провайдера"
    echo "  smoke-search   - Проверка поиска по каталогу"
    echo "  smoke-api      - Проверка API endpoints"
    echo
    echo -e "${GREEN}Обслуживание:${NC}"
    echo "  backup    - Создать резервную копию"
    echo "  health    - Быстрая проверка здоровья"
    echo
    echo -e "${GREEN}Примеры:${NC}"
    echo "  $0 start           # Запустить бота"
    echo "  $0 restart         # Перезапуск с пересборкой"
    echo "  $0 update-stash    # Обновить код с сохранением изменений"
    echo "  $0 logs-app        # Только логи приложения"
    echo "  $0 status          # Полный статус"
    echo
}

# Получаем команду
COMMAND=${1:-"help"}
SCRIPTS_DIR="/opt/llm-bot/scripts"

case $COMMAND in
    "start")
        log "🚀 Запуск production приложения..."
        $SCRIPTS_DIR/start_production.sh
        ;;
    
    "stop")
        log "🛑 Остановка production приложения..."
        $SCRIPTS_DIR/prod_stop.sh
        ;;
    
    "restart")
        log "🔄 Перезапуск production приложения..."
        $SCRIPTS_DIR/prod_restart.sh
        ;;
    
    "status")
        log "📊 Проверка статуса приложения..."
        $SCRIPTS_DIR/prod_status.sh
        ;;
    
    "logs")
        log "📋 Показ логов всех сервисов..."
        $SCRIPTS_DIR/prod_logs.sh
        ;;
    
    "logs-app")
        log "📋 Показ логов веб-приложения..."
        $SCRIPTS_DIR/prod_logs.sh app
        ;;
    
    "logs-bot")
        log "📋 Показ логов Telegram бота..."
        $SCRIPTS_DIR/prod_logs.sh bot
        ;;
    
    "logs-db"|"logs-postgres")
        log "📋 Показ логов базы данных..."
        $SCRIPTS_DIR/prod_logs.sh postgres
        ;;
    
    "update")
        log "🛡️ Безопасное обновление приложения..."
        if [ -f "$SCRIPTS_DIR/update_safe.sh" ]; then
            $SCRIPTS_DIR/update_safe.sh
        else
            error "Скрипт update_safe.sh не найден!"
        fi
        ;;
    
    "update-stash")
        log "💾 Обновление с сохранением локальных изменений..."
        if [ -f "$SCRIPTS_DIR/update_stash.sh" ]; then
            $SCRIPTS_DIR/update_stash.sh
        else
            error "Скрипт update_stash.sh не найден!"
        fi
        ;;
    
    "update-force")
        log "🔨 Принудительное обновление..."
        if [ -f "$SCRIPTS_DIR/update_force.sh" ]; then
            $SCRIPTS_DIR/update_force.sh
        else
            error "Скрипт update_force.sh не найден!"
        fi
        ;;
    
    "test")
        log "🧪 Запуск всех тестов..."
        if [ -f "$SCRIPTS_DIR/run_tests.sh" ]; then
            $SCRIPTS_DIR/run_tests.sh all
        else
            error "Скрипт run_tests.sh не найден!"
        fi
        ;;
    
    "test-fast")
        log "⚡ Запуск быстрых тестов..."
        if [ -f "$SCRIPTS_DIR/run_tests.sh" ]; then
            $SCRIPTS_DIR/run_tests.sh fast
        else
            error "Скрипт run_tests.sh не найден!"
        fi
        ;;
    
    "test-coverage")
        log "📊 Запуск тестов с покрытием..."
        if [ -f "$SCRIPTS_DIR/run_tests.sh" ]; then
            $SCRIPTS_DIR/run_tests.sh coverage
        else
            error "Скрипт run_tests.sh не найден!"
        fi
        ;;
    
    "smoke")
        log "🔥 Запуск всех smoke tests..."
        if [ -f "$SCRIPTS_DIR/smoke_tests.sh" ]; then
            $SCRIPTS_DIR/smoke_tests.sh all
        else
            error "Скрипт smoke_tests.sh не найден!"
        fi
        ;;
    
    "smoke-db")
        log "🗄️ Проверка подключения к БД..."
        if [ -f "$SCRIPTS_DIR/smoke_tests.sh" ]; then
            $SCRIPTS_DIR/smoke_tests.sh database
        else
            error "Скрипт smoke_tests.sh не найден!"
        fi
        ;;
    
    "smoke-llm")
        log "🧠 Проверка LLM провайдера..."
        if [ -f "$SCRIPTS_DIR/smoke_tests.sh" ]; then
            $SCRIPTS_DIR/smoke_tests.sh llm
        else
            error "Скрипт smoke_tests.sh не найден!"
        fi
        ;;
    
    "smoke-search")
        log "🔍 Проверка поиска по каталогу..."
        if [ -f "$SCRIPTS_DIR/smoke_tests.sh" ]; then
            $SCRIPTS_DIR/smoke_tests.sh search
        else
            error "Скрипт smoke_tests.sh не найден!"
        fi
        ;;
    
    "smoke-api")
        log "🌐 Проверка API endpoints..."
        if [ -f "$SCRIPTS_DIR/smoke_tests.sh" ]; then
            $SCRIPTS_DIR/smoke_tests.sh api
        else
            error "Скрипт smoke_tests.sh не найден!"
        fi
        ;;
    
    "backup")
        log "💾 Создание резервной копии..."
        if [ -f "$SCRIPTS_DIR/backup.sh" ]; then
            $SCRIPTS_DIR/backup.sh
        else
            error "Скрипт backup.sh не найден!"
        fi
        ;;
    
    "health")
        log "🔍 Быстрая проверка здоровья..."
        cd /opt/llm-bot/app
        
        # Проверяем контейнеры
        RUNNING=$(docker-compose -f docker-compose.prod.yml ps | grep "Up" | wc -l)
        if [ $RUNNING -ge 2 ]; then
            success "Контейнеры запущены ($RUNNING/3)"
        else
            warning "Запущено только $RUNNING контейнера из 3"
        fi
        
        # Проверяем health endpoint
        if curl -s http://localhost:8000/health > /dev/null; then
            success "Health endpoint отвечает"
        else
            error "Health endpoint недоступен"
        fi
        
        success "Быстрая проверка завершена"
        ;;
    
    "help"|"--help"|"-h")
        show_help
        ;;
    
    *)
        error "Неизвестная команда: $COMMAND"
        echo
        show_help
        ;;
esac
