#!/bin/bash
# Скрипт тестирования перед деплоем
# Использование: ./scripts/test_and_deploy.sh

set -e

# Цвета для вывода  
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[TEST&DEPLOY]${NC} $1"
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

# Переходим в директорию проекта
cd "$(dirname "$0")/.."

log "🚀 Начинаем процесс тестирования и деплоя..."

# 1. Проверяем что нет незафиксированных изменений
log "📋 Проверяем статус Git..."
if ! git diff-index --quiet HEAD --; then
    warning "Обнаружены незафиксированные изменения в Git"
    echo "Зафиксированные изменения:"
    git status --porcelain
    echo
    read -p "Продолжить с незафиксированными изменениями? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        error "Операция отменена. Зафиксируйте изменения и повторите."
    fi
fi

# 2. Запускаем линтеры
log "🔍 Проверяем качество кода..."

if command -v black &> /dev/null; then
    log "Запускаем black..."
    black --check src/ tests/ || error "Black проверка не пройдена! Запустите: black src/ tests/"
else
    warning "Black не установлен, пропускаем проверку форматирования"
fi

if command -v isort &> /dev/null; then
    log "Запускаем isort..."
    isort --check-only src/ tests/ || error "isort проверка не пройдена! Запустите: isort src/ tests/"
else
    warning "isort не установлен, пропускаем проверку импортов"
fi

if command -v flake8 &> /dev/null; then
    log "Запускаем flake8..."
    flake8 src/ tests/ || error "flake8 проверка не пройдена!"
else
    warning "flake8 не установлен, пропускаем проверку стиля"
fi

success "Проверки качества кода пройдены"

# 3. Запускаем быстрые тесты
log "⚡ Запускаем быстрые тесты..."
if ! ./scripts/run_tests.sh fast; then
    error "Быстрые тесты не пройдены!"
fi

success "Быстрые тесты пройдены"

# 4. Запускаем полные тесты
log "🧪 Запускаем полные тесты..."
if ! ./scripts/run_tests.sh all; then
    warning "Полные тесты не пройдены!"
    echo
    read -p "Продолжить деплой несмотря на провалившиеся тесты? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        error "Деплой отменен из-за провалившихся тестов"
    fi
    warning "Деплой продолжается несмотря на провалившиеся тесты!"
else
    success "Все тесты пройдены"
fi

# 5. Генерируем отчет о покрытии
log "📊 Генерируем отчет о покрытии..."
if ./scripts/run_tests.sh coverage; then
    success "Отчет о покрытии создан в htmlcov/"
else
    warning "Не удалось создать отчет о покрытии"
fi

# 6. Проверяем подключение к серверу
log "🌐 Проверяем подключение к production серверу..."
if ! ssh root@5.129.224.104 "echo 'Подключение успешно'"; then
    error "Не удается подключиться к production серверу!"
fi

success "Подключение к серверу работает"

# 7. Запрашиваем подтверждение деплоя  
echo
echo "=== ГОТОВНОСТЬ К ДЕПЛОЮ ==="
echo "✅ Качество кода проверено"
echo "✅ Быстрые тесты пройдены"
echo "✅ Полные тесты выполнены"
echo "✅ Подключение к серверу работает"
echo

read -p "🚀 Начать деплой на production? (y/N): " deploy_confirm
if [[ $deploy_confirm != [yY] ]]; then
    warning "Деплой отменен пользователем"
    exit 0
fi

# 8. Выполняем деплой
log "🚀 Начинаем деплой на production..."

# Коммитим текущие изменения если есть
if ! git diff-index --quiet HEAD --; then
    log "📝 Коммитим текущие изменения..."
    COMMIT_MSG="deploy: Автоматический коммит перед деплоем $(date +'%Y-%m-%d %H:%M:%S')"
    git add .
    git commit -m "$COMMIT_MSG"
    success "Изменения закоммичены"
fi

# Пушим в репозиторий
log "📤 Отправляем изменения в репозиторий..."
git push origin main
success "Изменения отправлены в репозиторий"

# Запускаем обновление на сервере
log "🔄 Обновляем приложение на сервере..."
ssh root@5.129.224.104 "bot update-stash"

# Проверяем статус после деплоя
log "🔍 Проверяем статус после деплоя..."
if ssh root@5.129.224.104 "bot health"; then
    success "Деплой завершен успешно!"
    success "Приложение работает на production"
else
    error "Проблемы после деплоя! Проверьте статус: ssh root@5.129.224.104 'bot status'"
fi

# Показываем итоговую информацию
echo
echo "=== ДЕПЛОЙ ЗАВЕРШЕН ==="
echo "📅 Время: $(date)"
echo "🌐 URL: http://5.129.224.104:8000"
echo "🔍 Health: http://5.129.224.104:8000/health"
echo "📊 Статус: ssh root@5.129.224.104 'bot status'"
echo
success "🎉 Все готово! Приложение обновлено на production"
