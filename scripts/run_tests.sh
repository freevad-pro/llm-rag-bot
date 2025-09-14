#!/bin/bash
# Скрипт для запуска тестов ИИ-бота
# Использование: ./scripts/run_tests.sh [тип_тестов]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[TESTS]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

# Переходим в директорию проекта
cd "$(dirname "$0")/.."

# Проверяем наличие pytest
if ! command -v pytest &> /dev/null; then
    error "pytest не установлен! Установите: poetry install"
    exit 1
fi

# Функция показа справки
show_help() {
    echo "🧪 Скрипт запуска тестов ИИ-бота"
    echo
    echo "Использование: $0 [тип_тестов] [опции]"
    echo
    echo "Типы тестов:"
    echo "  all         - Все тесты (по умолчанию)"
    echo "  unit        - Только unit тесты (быстрые)"
    echo "  integration - Только интеграционные тесты"
    echo "  e2e         - Только E2E тесты (медленные)"
    echo "  db          - Только тесты базы данных"
    echo "  api         - Только тесты API"
    echo "  telegram    - Только тесты Telegram бота"
    echo "  llm         - Только тесты LLM провайдеров"
    echo "  search      - Только тесты поиска"
    echo "  leads       - Только тесты управления лидами"
    echo
    echo "Специальные режимы:"
    echo "  fast        - Только быстрые тесты (unit + некоторые integration)"
    echo "  slow        - Только медленные тесты"
    echo "  coverage    - Запуск с покрытием кода"
    echo "  parallel    - Параллельный запуск (быстрее)"
    echo
    echo "Опции:"
    echo "  -v, --verbose    - Подробный вывод"
    echo "  -x, --exitfirst  - Остановка на первой ошибке"
    echo "  -k PATTERN       - Запуск тестов по паттерну имени"
    echo "  --html           - Генерация HTML отчета"
    echo
    echo "Примеры:"
    echo "  $0 unit                 # Только unit тесты"
    echo "  $0 integration -v       # Интеграционные тесты с подробным выводом"
    echo "  $0 fast --html          # Быстрые тесты с HTML отчетом"
    echo "  $0 -k test_lead         # Тесты содержащие 'test_lead'"
    echo
}

# Получаем тип тестов
TEST_TYPE=${1:-"all"}
shift || true  # Убираем первый аргумент

# Базовые опции pytest
PYTEST_ARGS="-v --tb=short --disable-warnings"

# Добавляем дополнительные аргументы
PYTEST_ARGS="$PYTEST_ARGS $@"

case $TEST_TYPE in
    "all")
        log "🚀 Запуск всех тестов..."
        MARKERS=""
        ;;
    
    "unit")
        log "⚡ Запуск unit тестов..."
        MARKERS="-m unit"
        ;;
    
    "integration")
        log "🔗 Запуск интеграционных тестов..."
        MARKERS="-m integration"
        ;;
    
    "e2e")
        log "🎯 Запуск E2E тестов..."
        MARKERS="-m e2e"
        ;;
    
    "db")
        log "🗄️ Запуск тестов базы данных..."
        MARKERS="-m db"
        ;;
    
    "api")
        log "🌐 Запуск тестов API..."
        MARKERS="-m api"
        ;;
    
    "telegram")
        log "📱 Запуск тестов Telegram бота..."
        MARKERS="-m telegram"
        ;;
    
    "llm")
        log "🧠 Запуск тестов LLM провайдеров..."
        MARKERS="-m llm"
        ;;
    
    "search")
        log "🔍 Запуск тестов поиска..."
        MARKERS="-m search"
        ;;
    
    "leads")
        log "👥 Запуск тестов управления лидами..."
        MARKERS="-m leads"
        ;;
    
    "fast")
        log "⚡ Запуск быстрых тестов..."
        MARKERS="-m 'unit or (integration and not slow)'"
        ;;
    
    "slow")
        log "🐌 Запуск медленных тестов..."
        MARKERS="-m slow"
        ;;
    
    "coverage")
        log "📊 Запуск тестов с покрытием кода..."
        MARKERS=""
        PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=html --cov-report=term-missing"
        ;;
    
    "parallel")
        log "🚀 Параллельный запуск тестов..."
        MARKERS=""
        PYTEST_ARGS="$PYTEST_ARGS -n auto"
        ;;
    
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    
    *)
        error "Неизвестный тип тестов: $TEST_TYPE"
        echo
        show_help
        exit 1
        ;;
esac

# Проверяем наличие тестов
if [ ! -d "tests" ]; then
    error "Директория tests не найдена!"
    exit 1
fi

# Запускаем тесты
log "Команда: pytest $PYTEST_ARGS $MARKERS tests/"
echo

START_TIME=$(date +%s)

if pytest $PYTEST_ARGS $MARKERS tests/; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    success "Все тесты пройдены успешно!"
    success "Время выполнения: ${DURATION} секунд"
    
    # Показываем дополнительную информацию
    if [[ "$PYTEST_ARGS" == *"--cov"* ]]; then
        echo
        log "📊 Отчет о покрытии создан в htmlcov/index.html"
    fi
    
    if [[ "$PYTEST_ARGS" == *"--html"* ]]; then
        echo
        log "📄 HTML отчет создан в report.html"
    fi
    
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    error "Некоторые тесты провалились!"
    error "Время выполнения: ${DURATION} секунд"
    
    echo
    warning "Для подробной информации запустите с опцией -v"
    warning "Для остановки на первой ошибке используйте -x"
    
    exit 1
fi
