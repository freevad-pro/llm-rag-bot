#!/bin/bash
# Скрипт для полной очистки и пересоздания миграций Alembic
# Использование: ./scripts/reset_migrations.sh

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

log "🔄 Начинаем полную очистку и пересоздание миграций..."

# Проверяем, что мы в правильной директории
if [ ! -f "alembic.ini" ]; then
    error "Файл alembic.ini не найден! Запустите скрипт из корня проекта."
fi

# Создаем backup текущих миграций
log "📦 Создаем backup текущих миграций..."
BACKUP_DIR="migrations_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r src/infrastructure/database/migrations/versions "$BACKUP_DIR/"
success "✅ Backup создан в директории: $BACKUP_DIR"

# Останавливаем приложение
log "⏹️ Останавливаем приложение..."
docker-compose -f docker-compose.prod.yml stop app || true

# Удаляем таблицу alembic_version из БД (если приложение запущено)
log "🗑️ Очищаем историю миграций в БД..."
if docker-compose -f docker-compose.prod.yml ps postgres | grep -q "Up"; then
    docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "DROP TABLE IF EXISTS alembic_version CASCADE;" || true
    success "✅ Таблица alembic_version удалена из БД"
else
    warning "⚠️ PostgreSQL не запущен, пропускаем очистку БД"
fi

# Удаляем все файлы миграций
log "🗑️ Удаляем все файлы миграций..."
rm -rf src/infrastructure/database/migrations/versions/*
success "✅ Все файлы миграций удалены"

# Создаем начальную миграцию с текущим состоянием моделей
log "🏗️ Создаем начальную миграцию с текущим состоянием..."
docker-compose -f docker-compose.prod.yml run --rm app alembic revision --autogenerate -m "Initial migration with current schema"

# Проверяем, что миграция создана
MIGRATION_FILE=$(ls src/infrastructure/database/migrations/versions/ | head -1)
if [ -z "$MIGRATION_FILE" ]; then
    error "❌ Начальная миграция не была создана!"
fi

log "📝 Создана миграция: $MIGRATION_FILE"

# Переименовываем миграцию в правильный формат
NEW_NAME="001_initial_migration.py"
mv "src/infrastructure/database/migrations/versions/$MIGRATION_FILE" "src/infrastructure/database/migrations/versions/$NEW_NAME"

# Обновляем содержимое миграции для правильной нумерации
log "📝 Обновляем содержимое миграции..."
sed -i 's/revision = .*/revision = "001_initial_migration"/' "src/infrastructure/database/migrations/versions/$NEW_NAME"
sed -i 's/down_revision = .*/down_revision = None/' "src/infrastructure/database/migrations/versions/$NEW_NAME"

success "✅ Начальная миграция создана: $NEW_NAME"

# Запускаем приложение
log "▶️ Запускаем приложение..."
docker-compose -f docker-compose.prod.yml up -d

# Ждем готовности
log "⏳ Ожидаем готовности приложения..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec app python -c "import requests; requests.get('http://localhost:8000/health')" > /dev/null 2>&1; then
        success "✅ Приложение готово"
        break
    fi
    if [ $i -eq 30 ]; then
        error "❌ Приложение не стартовало за 30 секунд"
    fi
    sleep 1
done

# Применяем миграцию
log "🚀 Применяем начальную миграцию..."
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

success "✅ Миграция применена успешно"

# Проверяем статус
log "📊 Проверяем статус миграций..."
docker-compose -f docker-compose.prod.yml exec app alembic current
docker-compose -f docker-compose.prod.yml exec app alembic history

success "🎉 Миграции успешно сброшены и пересозданы!"

echo
echo "=== РЕЗУЛЬТАТ ==="
echo "📦 Backup старых миграций: $BACKUP_DIR"
echo "📝 Новая миграция: $NEW_NAME"
echo "🗄️ БД обновлена до текущего состояния схемы"
echo
echo "=== ДАЛЬНЕЙШИЕ ДЕЙСТВИЯ ==="
echo "1. Все новые миграции будут создаваться с правильной нумерацией"
echo "2. Для создания новой миграции используйте:"
echo "   docker-compose -f docker-compose.prod.yml exec app alembic revision --autogenerate -m 'Описание изменений'"
echo "3. Для применения миграций:"
echo "   docker-compose -f docker-compose.prod.yml exec app alembic upgrade head"
echo
warning "⚠️ Старые миграции сохранены в $BACKUP_DIR на случай необходимости отката"
