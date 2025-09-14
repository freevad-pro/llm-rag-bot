#!/bin/bash
# Скрипт запуска smoke tests на VPS
# Использование: ./scripts/smoke_tests.sh [тест]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[SMOKE]${NC} $1"
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Проверяем что мы на VPS (есть production контейнеры)
if ! docker ps | grep -q "llm-rag-bot"; then
    error "Production контейнеры не запущены! Запустите сначала: bot start"
    exit 1
fi

# Функция показа справки
show_help() {
    echo "🔥 Smoke tests для VPS - быстрые проверки работоспособности"
    echo
    echo "Использование: $0 [тест] [опции]"
    echo
    echo "Доступные тесты:"
    echo "  all        - Все smoke tests (по умолчанию)"
    echo "  database   - Проверка подключения к БД"
    echo "  llm        - Проверка LLM провайдера"
    echo "  search     - Проверка поиска по каталогу"
    echo "  user       - Проверка создания пользователя"
    echo "  api        - Проверка API endpoints"
    echo
    echo "Опции:"
    echo "  -v, --verbose  - Подробный вывод"
    echo "  -h, --help     - Показать справку"
    echo
    echo "Примеры:"
    echo "  $0              # Все tests"
    echo "  $0 database     # Только БД"
    echo "  $0 llm -v       # LLM с подробным выводом"
    echo
    echo "⚡ Время выполнения: 15-30 секунд"
    echo "🧹 Тестовые данные автоматически удаляются"
}

# Разбор аргументов
TEST_TYPE="all"
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        all|database|llm|search|user|api)
            TEST_TYPE="$1"
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "Неизвестный аргумент: $1"
            show_help
            exit 1
            ;;
    esac
done

# Функция запуска smoke test через Docker
run_smoke_test() {
    local test_name="$1"
    
    log "Запуск smoke test: $test_name"
    
    # Создаем Python скрипт для выполнения
    cat > "/tmp/smoke_test_runner.py" << EOF
import asyncio
import sys
import json
sys.path.append('/app')

from src.infrastructure.testing.smoke_tests import run_smoke_tests, run_single_smoke_test

async def main():
    try:
        if "$test_name" == "all":
            results = await run_smoke_tests()
        else:
            results = await run_single_smoke_test("$test_name")
        
        print("SMOKE_TEST_RESULTS:" + json.dumps(results))
        
        if "$test_name" == "all":
            if results["failed"] > 0:
                sys.exit(1)
        else:
            if results["status"] == "FAILED":
                sys.exit(1)
                
    except Exception as e:
        print(f"SMOKE_TEST_ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
EOF

    # Запускаем тест в production контейнере
    local container_name=$(docker ps --format "table {{.Names}}" | grep "llm-rag-bot" | head -1)
    
    if [ -z "$container_name" ]; then
        error "Production контейнер не найден!"
        return 1
    fi
    
    log "Выполнение в контейнере: $container_name"
    
    # Копируем скрипт в контейнер и запускаем
    docker cp "/tmp/smoke_test_runner.py" "$container_name:/tmp/"
    
    local start_time=$(date +%s)
    
    if docker exec "$container_name" python /tmp/smoke_test_runner.py; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        success "Smoke test '$test_name' завершен успешно за ${duration}s"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        error "Smoke test '$test_name' провалился за ${duration}s"
        return 1
    fi
}

# Функция парсинга и отображения результатов
show_results() {
    local output="$1"
    
    # Ищем JSON результаты в выводе
    local json_line=$(echo "$output" | grep "SMOKE_TEST_RESULTS:" | sed 's/SMOKE_TEST_RESULTS://')
    
    if [ -n "$json_line" ]; then
        echo
        log "📊 Результаты smoke tests:"
        echo "$json_line" | python3 -c "
import sys, json
data = json.load(sys.stdin)

if 'total_tests' in data:
    # Результаты всех тестов
    print(f\"📈 Всего тестов: {data['total_tests']}\")
    print(f\"✅ Пройдено: {data['passed']}\")
    print(f\"❌ Провалено: {data['failed']}\")
    print(f\"📅 Время: {data['timestamp']}\")
    print()
    
    for test_name, result in data['tests'].items():
        status_icon = '✅' if result['status'] == 'PASSED' else '❌'
        duration = result['duration_seconds']
        print(f\"{status_icon} {test_name}: {result['status']} ({duration:.2f}s)\")
        
        if result['error']:
            print(f\"   🔍 Ошибка: {result['error']}\")
else:
    # Результат одного теста
    status_icon = '✅' if data['status'] == 'PASSED' else '❌'
    duration = data['duration_seconds']
    print(f\"{status_icon} {data['test']}: {data['status']} ({duration:.2f}s)\")
    
    if data['error']:
        print(f\"🔍 Ошибка: {data['error']}\")
"
    fi
    
    # Показываем ошибки если есть
    local error_line=$(echo "$output" | grep "SMOKE_TEST_ERROR:")
    if [ -n "$error_line" ]; then
        echo
        error "Критическая ошибка:"
        echo "$error_line" | sed 's/SMOKE_TEST_ERROR: //'
    fi
}

# Основная логика
main() {
    echo "🔥 Smoke Tests для VPS"
    echo "═══════════════════════"
    echo
    
    local overall_start=$(date +%s)
    
    # Запуск тестов
    local output=""
    local exit_code=0
    
    if [ "$VERBOSE" = true ]; then
        log "Режим: подробный вывод"
        output=$(run_smoke_test "$TEST_TYPE" 2>&1) || exit_code=$?
        echo "$output"
    else
        output=$(run_smoke_test "$TEST_TYPE" 2>&1) || exit_code=$?
    fi
    
    # Показываем результаты
    show_results "$output"
    
    local overall_end=$(date +%s)
    local total_duration=$((overall_end - overall_start))
    
    echo
    echo "════════════════════════════════════"
    
    if [ $exit_code -eq 0 ]; then
        success "Все smoke tests пройдены! Система работает корректно."
        success "⏱️ Общее время: ${total_duration} секунд"
    else
        error "Обнаружены проблемы в системе!"
        error "⏱️ Время до ошибки: ${total_duration} секунд"
        warning "💡 Рекомендация: проверьте логи через 'bot logs'"
    fi
    
    # Очистка временных файлов
    rm -f "/tmp/smoke_test_runner.py"
    
    exit $exit_code
}

# Проверка прав доступа
if [ "$EUID" -eq 0 ]; then
    warning "Запуск от root не рекомендуется"
fi

# Запуск
main "$@"
