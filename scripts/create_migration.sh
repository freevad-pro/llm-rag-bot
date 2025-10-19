#!/bin/bash
# Скрипт для создания новых миграций с правильной нумерацией
# Использование: ./scripts/create_migration.sh "Описание миграции"

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверяем аргументы
if [ $# -eq 0 ]; then
    error "Использование: $0 \"Описание миграции\""
fi

MIGRATION_DESCRIPTION="$1"

log "🔧 Создаем новую миграцию: $MIGRATION_DESCRIPTION"

# Проверяем, что мы в правильной директории
if [ ! -f "alembic.ini" ]; then
    error "Файл alembic.ini не найден! Запустите скрипт из корня проекта."
fi

# Определяем следующий номер миграции
log "🔍 Определяем следующий номер миграции..."
MIGRATIONS_DIR="src/infrastructure/database/migrations/versions"
LAST_MIGRATION=$(ls "$MIGRATIONS_DIR"/*.py 2>/dev/null | sort -V | tail -1 | sed 's/.*\///; s/\.py$//' | grep -o '^[0-9]*' || echo "0")
NEXT_NUMBER=$((LAST_MIGRATION + 1))
NEXT_NUMBER_PADDED=$(printf "%03d" $NEXT_NUMBER)

log "📝 Следующий номер миграции: $NEXT_NUMBER_PADDED"

# Создаем имя файла миграции
MIGRATION_NAME="${NEXT_NUMBER_PADDED}_$(echo "$MIGRATION_DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_\|_$//g')"
MIGRATION_FILE="$MIGRATIONS_DIR/${MIGRATION_NAME}.py"

log "📄 Имя файла миграции: $MIGRATION_NAME.py"

# Создаем миграцию
log "🏗️ Создаем миграцию..."
docker-compose -f docker-compose.prod.yml exec app alembic revision --autogenerate -m "$MIGRATION_DESCRIPTION"

# Находим созданный файл (он будет с хешем)
CREATED_FILE=$(find "$MIGRATIONS_DIR" -name "*$(echo "$MIGRATION_DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')*.py" | head -1)

if [ -z "$CREATED_FILE" ]; then
    # Если не нашли по описанию, берем самый новый файл
    CREATED_FILE=$(ls -t "$MIGRATIONS_DIR"/*.py | head -1)
fi

if [ -z "$CREATED_FILE" ]; then
    error "❌ Не удалось найти созданный файл миграции"
fi

log "📝 Создан файл: $(basename "$CREATED_FILE")"

# Переименовываем файл в правильный формат
mv "$CREATED_FILE" "$MIGRATION_FILE"
log "🔄 Переименован в: $(basename "$MIGRATION_FILE")"

# Исправляем содержимое файла
log "🔧 Исправляем содержимое миграции..."

# Определяем правильный down_revision (последнюю миграцию)
LAST_REVISION=$(ls "$MIGRATIONS_DIR"/*.py | grep -v "$MIGRATION_NAME" | sort -V | tail -1 | sed 's/.*\///; s/\.py$//')

# Обновляем содержимое файла
sed -i "s/revision = .*/revision = \"$MIGRATION_NAME\"/" "$MIGRATION_FILE"
sed -i "s/down_revision = .*/down_revision = \"$LAST_REVISION\"/" "$MIGRATION_FILE"

success "✅ Миграция создана и исправлена: $MIGRATION_NAME.py"

# Показываем содержимое для проверки
log "📋 Содержимое созданной миграции:"
head -20 "$MIGRATION_FILE"

echo
echo "=== РЕЗУЛЬТАТ ==="
echo "📝 Создана миграция: $MIGRATION_NAME.py"
echo "🔗 Связь: $LAST_REVISION -> $MIGRATION_NAME"
echo
echo "=== СЛЕДУЮЩИЕ ШАГИ ==="
echo "1. Проверьте содержимое миграции: $MIGRATION_FILE"
echo "2. При необходимости отредактируйте логику миграции"
echo "3. Примените миграцию: docker-compose -f docker-compose.prod.yml exec app alembic upgrade head"
echo "4. Проверьте результат: docker-compose -f docker-compose.prod.yml exec app alembic current"
