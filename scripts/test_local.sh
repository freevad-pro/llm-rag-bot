#!/bin/bash
# Скрипт для локального тестирования
# Использование: ./scripts/test_local.sh [команда]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[LOCAL TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
    exit 1
}

info() {
    echo -e "${CYAN}ℹ️${NC} $1"
}

# Переходим в директорию проекта
cd "$(dirname "$0")/.."

# Функция показа справки
show_help() {
    echo -e "${CYAN}🧪 Локальное тестирование ИИ-бота${NC}"
    echo
    echo "Использование: $0 [команда] [опции]"
    echo
    echo -e "${GREEN}Управление средой:${NC}"
    echo "  setup      - Настроить тестовую среду"
    echo "  start      - Запустить тестовую среду"
    echo "  stop       - Остановить тестовую среду"
    echo "  clean      - Очистить тестовую среду"
    echo "  logs       - Показать логи сервисов"
    echo
    echo -e "${GREEN}Тестирование:${NC}"
    echo "  test       - Запустить все тесты"
    echo "  test-unit  - Только unit тесты"
    echo "  test-int   - Только интеграционные тесты"
    echo "  test-e2e   - Только E2E тесты"
    echo "  test-watch - Тесты в режиме наблюдения"
    echo "  coverage   - Тесты с покрытием кода"
    echo
    echo -e "${GREEN}Качество кода:${NC}"
    echo "  lint       - Проверка качества кода"
    echo "  format     - Форматирование кода"
    echo "  check      - Полная проверка (lint + test)"
    echo
    echo -e "${GREEN}Отладка:${NC}"
    echo "  shell      - Интерактивная оболочка в контейнере"
    echo "  db-shell   - Подключение к тестовой БД"
    echo "  app-logs   - Логи приложения"
    echo "  status     - Статус всех сервисов"
    echo
    echo -e "${GREEN}Примеры:${NC}"
    echo "  $0 setup && $0 test     # Настроить и запустить тесты"
    echo "  $0 test-watch           # Тесты с автоперезапуском"
    echo "  $0 check                # Полная проверка кода"
    echo
}

# Функция проверки Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker не установлен!"
    fi
    
    if ! docker compose version &> /dev/null; then
        error "Docker Compose не установлен!"
    fi
}

# Функция настройки тестовой среды
setup_environment() {
    log "🔧 Настройка тестовой среды..."
    
    # Создаем директории для тестов
    mkdir -p data/test_chroma data/test_uploads test-results htmlcov
    
    # Создаем тестовый .env файл если его нет
    if [ ! -f ".env.test" ]; then
        log "📝 Создаем .env.test файл..."
        cat > .env.test << EOF
# Тестовая конфигурация
DEBUG=true
ENVIRONMENT=test
DATABASE_URL=postgresql+asyncpg://test_user:test_pass@localhost:5433/test_catalog_db
BOT_TOKEN=test_bot_token_for_local_testing
DEFAULT_LLM_PROVIDER=test
MANAGER_TELEGRAM_CHAT_ID=
ADMIN_TELEGRAM_IDS=
LEAD_INACTIVITY_THRESHOLD=1
EOF
        success "Создан .env.test файл"
    fi
    
    # Создаем скрипт инициализации тестовых данных
    if [ ! -f "scripts/init_test_data.sql" ]; then
        log "📝 Создаем скрипт инициализации тестовых данных..."
        cat > scripts/init_test_data.sql << 'EOF'
-- Инициализация тестовых данных
-- Этот скрипт выполняется при создании тестовой БД

-- Создаем тестового пользователя для интеграционных тестов
INSERT INTO users (chat_id, telegram_user_id, username, first_name, last_name, phone, email) 
VALUES (999999, 888888, 'test_user', 'Тестовый', 'Пользователь', '+79001234567', 'test@example.com')
ON CONFLICT (chat_id) DO NOTHING;

-- Создаем тестовые настройки LLM
INSERT INTO llm_settings (provider, config, is_active, created_at)
VALUES 
    ('test', '{"api_key": "test_key", "model": "test-model"}', true, NOW()),
    ('openai', '{"api_key": "test_openai_key", "model": "gpt-3.5-turbo"}', false, NOW())
ON CONFLICT DO NOTHING;

-- Добавляем тестовые категории товаров
-- (здесь можно добавить другие тестовые данные)
EOF
        success "Создан скрипт инициализации тестовых данных"
    fi
    
    success "Тестовая среда настроена"
}

# Получаем команду
COMMAND=${1:-"help"}
shift || true

case $COMMAND in
    "setup")
        check_docker
        setup_environment
        log "🐳 Собираем тестовые образы..."
        docker compose -f docker-compose.test.yml build
        success "Тестовая среда готова к использованию"
        ;;
    
    "start")
        check_docker
        log "🚀 Запуск тестовой среды..."
        docker compose -f docker-compose.test.yml up -d postgres-test
        
        # Ждем готовности БД
        log "⏳ Ожидание готовности PostgreSQL..."
        sleep 5
        
        docker compose -f docker-compose.test.yml up -d app-test
        
        log "⏳ Ожидание готовности приложения..."
        sleep 10
        
        # Проверяем статус
        if curl -s http://localhost:8001/health > /dev/null; then
            success "Тестовая среда запущена!"
            info "🌐 Приложение: http://localhost:8001"
            info "🗄️ БД: localhost:5433"
            info "📋 Health: http://localhost:8001/health"
        else
            warning "Приложение не отвечает. Проверьте логи: $0 logs"
        fi
        ;;
    
    "stop")
        log "🛑 Остановка тестовой среды..."
        docker compose -f docker-compose.test.yml down
        success "Тестовая среда остановлена"
        ;;
    
    "clean")
        log "🧹 Очистка тестовой среды..."
        docker compose -f docker-compose.test.yml down -v --remove-orphans
        docker compose -f docker-compose.test.yml build --no-cache
        rm -rf data/test_chroma/* data/test_uploads/* test-results/* htmlcov/*
        success "Тестовая среда очищена"
        ;;
    
    "test")
        log "🧪 Запуск всех тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test $@
        ;;
    
    "test-unit")
        log "⚡ Запуск unit тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m unit $@
        ;;
    
    "test-int")
        log "🔗 Запуск интеграционных тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m integration $@
        ;;
    
    "test-e2e")
        log "🎯 Запуск E2E тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m e2e $@
        ;;
    
    "test-watch")
        log "👀 Запуск тестов в режиме наблюдения..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test-watch $@
        ;;
    
    "coverage")
        log "📊 Запуск тестов с покрытием..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner coverage $@
        success "Отчет сохранен в htmlcov/index.html"
        ;;
    
    "lint")
        log "🔍 Проверка качества кода..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner lint
        ;;
    
    "format")
        log "✨ Форматирование кода..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner format
        ;;
    
    "check")
        log "🔎 Полная проверка кода..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner lint
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m "unit or (integration and not slow)"
        success "Полная проверка завершена"
        ;;
    
    "shell")
        log "🐚 Интерактивная оболочка..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner shell
        ;;
    
    "db-shell")
        log "🗄️ Подключение к тестовой БД..."
        docker compose -f docker-compose.test.yml exec postgres-test psql -U test_user -d test_catalog_db
        ;;
    
    "logs")
        log "📋 Логи сервисов..."
        docker compose -f docker-compose.test.yml logs -f ${1:-}
        ;;
    
    "app-logs")
        log "📋 Логи приложения..."
        docker compose -f docker-compose.test.yml logs -f app-test
        ;;
    
    "status")
        log "📊 Статус сервисов..."
        docker compose -f docker-compose.test.yml ps
        echo
        if curl -s http://localhost:8001/health > /dev/null; then
            success "Приложение работает: http://localhost:8001"
        else
            warning "Приложение недоступно"
        fi
        ;;
    
    "help"|"-h"|"--help")
        show_help
        ;;
    
    *)
        error "Неизвестная команда: $COMMAND"
        echo
        show_help
        ;;
esac
