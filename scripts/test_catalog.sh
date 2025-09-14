#!/bin/bash
# Скрипт для тестирования системы каталога
# Использование: ./scripts/test_catalog.sh [тип_тестов]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[CATALOG-TESTS]${NC} $1"
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

# Проверяем что находимся в корне проекта
if [ ! -f "pyproject.toml" ]; then
    error "Запустите скрипт из корня проекта"
    exit 1
fi

# Определяем тип тестов
TEST_TYPE=${1:-"all"}

log "Тестирование системы каталога: $TEST_TYPE"

case $TEST_TYPE in
    "unit")
        log "Запуск UNIT тестов каталога (быстрые, с моками)"
        docker-compose -f docker-compose.test.yml exec app-test python -m pytest tests/unit/test_catalog_components.py -v -m "search and unit"
        ;;
    
    "integration") 
        log "Запуск INTEGRATION тестов каталога (с Chroma DB)"
        docker-compose -f docker-compose.test.yml exec app-test python -m pytest tests/integration/test_catalog_search.py -v -m "search and integration"
        ;;
    
    "e2e")
        log "Запуск E2E тестов каталога (полные сценарии)"
        docker-compose -f docker-compose.test.yml exec app-test python -m pytest tests/e2e/test_catalog_user_scenarios.py -v -m "search and e2e"
        ;;
    
    "fast")
        log "Запуск быстрых тестов каталога (unit + integration без slow)"
        docker-compose -f docker-compose.test.yml exec app-test python -m pytest -v -m "search and (unit or (integration and not slow))"
        ;;
    
    "all")
        log "Запуск ВСЕХ тестов каталога"
        docker-compose -f docker-compose.test.yml exec app-test python -m pytest -v -m search
        ;;
    
    "coverage")
        log "Запуск тестов каталога с покрытием кода"
        docker-compose -f docker-compose.test.yml exec app-test python -m pytest --cov=src.infrastructure.search --cov=src.domain.entities.product --cov-report=html --cov-report=term -v -m search
        ;;
    
    *)
        echo "Использование: $0 [unit|integration|e2e|fast|all|coverage]"
        echo ""
        echo "Типы тестов каталога:"
        echo "  unit        - Быстрые unit тесты с моками (< 1 сек)"
        echo "  integration - Тесты с Chroma DB (1-10 сек)" 
        echo "  e2e         - Полные пользовательские сценарии (10+ сек)"
        echo "  fast        - unit + integration без медленных"
        echo "  all         - Все тесты каталога"
        echo "  coverage    - Тесты с отчетом о покрытии кода"
        exit 1
        ;;
esac

success "Тесты каталога ($TEST_TYPE) завершены!"

# Дополнительная информация
if [ "$TEST_TYPE" = "coverage" ]; then
    log "Отчет о покрытии: htmlcov/index.html"
fi

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "e2e" ]; then
    warning "E2E тесты могут быть медленными при первой загрузке модели"
fi
