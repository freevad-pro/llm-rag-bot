#!/bin/bash
# Скрипт для исправления веток миграций без полного сброса
# Использование: ./scripts/fix_migration_branches.sh

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

log "🔧 Исправляем ветки миграций..."

# Проверяем, что мы в правильной директории
if [ ! -f "alembic.ini" ]; then
    error "Файл alembic.ini не найден! Запустите скрипт из корня проекта."
fi

# Создаем backup
log "📦 Создаем backup текущих миграций..."
BACKUP_DIR="migrations_fix_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r src/infrastructure/database/migrations/versions "$BACKUP_DIR/"
success "✅ Backup создан в директории: $BACKUP_DIR"

# Исправляем миграцию с хешем - переименовываем её в правильный формат
log "🔧 Исправляем миграцию с хешем..."
HASH_MIGRATION="src/infrastructure/database/migrations/versions/8bd76168eb7e_add_usage_statistics_table_for_ai_cost_.py"

if [ -f "$HASH_MIGRATION" ]; then
    # Переименовываем файл
    NEW_NAME="012_add_usage_statistics_table.py"
    mv "$HASH_MIGRATION" "src/infrastructure/database/migrations/versions/$NEW_NAME"
    
    # Исправляем содержимое файла
    log "📝 Обновляем содержимое миграции $NEW_NAME..."
    sed -i 's/revision = .*/revision = "012_add_usage_statistics_table"/' "src/infrastructure/database/migrations/versions/$NEW_NAME"
    sed -i 's/down_revision = .*/down_revision = "011_add_message_extra_data"/' "src/infrastructure/database/migrations/versions/$NEW_NAME"
    
    success "✅ Миграция переименована и исправлена: $NEW_NAME"
else
    warning "⚠️ Миграция с хешем не найдена, возможно уже исправлена"
fi

# Проверяем и исправляем другие потенциальные проблемы
log "🔍 Проверяем целостность цепочки миграций..."

# Список миграций в правильном порядке
MIGRATIONS=(
    "002_add_admin_tables"
    "003_classic_auth" 
    "004_add_prompt_metadata"
    "005_fix_company_services"
    "006_add_service_categories"
    "007_add_system_logs_columns"
    "008_rename_started_at_to_created_at"
    "009_add_catalog_versions_table"
    "010_fix_message_role_constraint"
    "011_add_message_extra_data"
    "012_add_usage_statistics_table"
)

# Проверяем, что все миграции существуют и имеют правильные связи
for i in "${!MIGRATIONS[@]}"; do
    CURRENT="${MIGRATIONS[$i]}"
    FILE="src/infrastructure/database/migrations/versions/${CURRENT}.py"
    
    if [ -f "$FILE" ]; then
        # Определяем правильный down_revision
        if [ $i -eq 0 ]; then
            DOWN_REVISION="None"
        else
            DOWN_REVISION="${MIGRATIONS[$((i-1))]}"
        fi
        
        # Проверяем и исправляем down_revision если нужно
        CURRENT_DOWN=$(grep "down_revision = " "$FILE" | sed 's/.*= *["'\'']//; s/["'\''].*//')
        if [ "$CURRENT_DOWN" != "$DOWN_REVISION" ]; then
            log "🔧 Исправляем down_revision в $CURRENT: $CURRENT_DOWN -> $DOWN_REVISION"
            sed -i "s/down_revision = .*/down_revision = \"$DOWN_REVISION\"/" "$FILE"
        fi
        
        success "✅ Миграция $CURRENT проверена"
    else
        warning "⚠️ Миграция $CURRENT не найдена"
    fi
done

# Проверяем валидность миграций
log "🧪 Проверяем валидность миграций..."
if docker-compose -f docker-compose.prod.yml exec app alembic check > /dev/null 2>&1; then
    success "✅ Все миграции валидны"
else
    warning "⚠️ Обнаружены проблемы в миграциях. Проверьте детали:"
    docker-compose -f docker-compose.prod.yml exec app alembic check
fi

# Показываем текущую историю
log "📋 Текущая история миграций:"
docker-compose -f docker-compose.prod.yml exec app alembic history

success "🎉 Ветки миграций исправлены!"

echo
echo "=== РЕЗУЛЬТАТ ==="
echo "📦 Backup создан в: $BACKUP_DIR"
echo "🔧 Миграции исправлены и выровнены в одну цепочку"
echo "📝 Правильная последовательность:"
for migration in "${MIGRATIONS[@]}"; do
    echo "   - $migration"
done
echo
echo "=== ДАЛЬНЕЙШИЕ ДЕЙСТВИЯ ==="
echo "1. Для применения миграций: docker-compose -f docker-compose.prod.yml exec app alembic upgrade head"
echo "2. Для создания новых миграций используйте правильный формат:"
echo "   docker-compose -f docker-compose.prod.yml exec app alembic revision --autogenerate -m '013_description'"
echo "3. Всегда проверяйте номер следующей миграции перед созданием"
