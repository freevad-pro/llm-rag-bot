#!/bin/bash
# Скрипт для полной очистки и пересоздания миграций Alembic
# Используется при проблемах с multiple heads или конфликтах миграций
# ВНИМАНИЕ: Удаляет ВСЕ данные из базы данных!

set -e

# Цвета для вывода
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка аргументов
FORCE=false
if [ "$1" = "--force" ]; then
    FORCE=true
fi

log "🔄 Скрипт полной очистки миграций Alembic"
echo
warning "⚠️  ВНИМАНИЕ: Этот скрипт удалит ВСЕ данные из базы данных!"
warning "⚠️  Используйте только при критических проблемах с миграциями!"
echo

if [ "$FORCE" != "true" ]; then
    read -p "Вы уверены, что хотите продолжить? Введите 'YES' для подтверждения: " confirm
    if [ "$confirm" != "YES" ]; then
        log "Операция отменена пользователем"
        exit 0
    fi
fi

# Переходим в рабочую директорию
cd /opt/llm-bot/app

# Проверяем, что мы в правильной директории
if [ ! -f "docker-compose.prod.yml" ]; then
    error "Файл docker-compose.prod.yml не найден. Убедитесь, что вы находитесь в правильной директории."
    exit 1
fi

log "📦 Создаем backup текущих миграций..."
backup_dir="migrations_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"

# Копируем файлы миграций если они есть
if [ -d "src/infrastructure/database/migrations/versions" ]; then
    cp -r src/infrastructure/database/migrations/versions "$backup_dir/"
    success "Backup миграций создан в директории: $backup_dir"
else
    log "Папка с миграциями не найдена, пропускаем backup"
fi

log "⏹️ Останавливаем все сервисы..."
docker-compose -f docker-compose.prod.yml down

log "🗑️ Удаляем данные PostgreSQL..."
if [ -d "/opt/llm-bot/data/postgres" ]; then
    rm -rf /opt/llm-bot/data/postgres/*
    success "Данные PostgreSQL удалены"
else
    warning "Папка с данными PostgreSQL не найдена"
fi

log "🗑️ Удаляем файлы миграций..."
if [ -d "src/infrastructure/database/migrations/versions" ]; then
    rm -rf src/infrastructure/database/migrations/versions/*
    success "Файлы миграций удалены"
else
    warning "Папка с миграциями не найдена"
fi

log "🔧 Проверяем alembic.ini..."
if [ ! -f "alembic.ini" ]; then
    error "Файл alembic.ini не найден!"
    exit 1
fi

# Проверяем правильность пути в alembic.ini
script_location=$(grep "script_location" alembic.ini | cut -d'=' -f2 | tr -d ' ')
if [ "$script_location" != "src/infrastructure/database/migrations" ]; then
    warning "Неправильный путь в alembic.ini: $script_location"
    warning "Ожидается: src/infrastructure/database/migrations"
fi

log "🏗️ Запускаем сервисы..."
docker-compose -f docker-compose.prod.yml up -d

log "⏳ Ожидаем запуска PostgreSQL..."
sleep 15

# Проверяем что сервисы запустились
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    error "Не удалось запустить сервисы"
    exit 1
fi

success "Сервисы запущены успешно"

log "🔍 Проверяем чистоту миграций..."
# Проверяем что папка versions пустая
if [ -d "src/infrastructure/database/migrations/versions" ]; then
    file_count=$(ls -1 src/infrastructure/database/migrations/versions/ 2>/dev/null | wc -l)
    if [ "$file_count" -eq 0 ]; then
        success "Папка versions пуста"
    else
        warning "В папке versions остались файлы: $file_count"
    fi
fi

log "📝 Создаем начальную миграцию..."
# Создаем пустую начальную миграцию
if docker-compose -f docker-compose.prod.yml exec app alembic revision -m "initial" > /dev/null 2>&1; then
    success "Начальная миграция создана"
else
    error "Не удалось создать начальную миграцию"
    exit 1
fi

log "🏷️ Помечаем БД начальной версией..."
# Помечаем БД этой версией (таблицы уже существуют)
if docker-compose -f docker-compose.prod.yml exec app alembic stamp head > /dev/null 2>&1; then
    success "База данных помечена начальной версией"
else
    error "Не удалось пометить базу данных"
    exit 1
fi

log "🔍 Проверяем результат..."
# Проверяем текущую версию
current_version=$(docker-compose -f docker-compose.prod.yml exec app alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)
if [ -n "$current_version" ]; then
    success "Текущая версия миграции: $current_version"
else
    warning "Не удалось определить текущую версию миграции"
fi

# Проверяем таблицу alembic_version
if docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT * FROM alembic_version;" > /dev/null 2>&1; then
    success "Таблица alembic_version создана и заполнена"
else
    warning "Проблемы с таблицей alembic_version"
fi

echo
success "🎉 Полная очистка миграций завершена успешно!"
echo
log "📋 Что было сделано:"
echo "   ✅ Создан backup старых миграций в: $backup_dir"
echo "   ✅ Очищены данные PostgreSQL"
echo "   ✅ Удалены старые файлы миграций"
echo "   ✅ Создана новая начальная миграция"
echo "   ✅ База данных помечена правильной версией"
echo
log "🚀 Теперь можно:"
echo "   • Создавать новые миграции: alembic revision --autogenerate -m 'description'"
echo "   • Применять миграции: alembic upgrade head"
echo "   • Проверять статус: alembic current"
echo
warning "📁 Backup старых миграций сохранен в: $backup_dir"
echo
log "✅ Готово к работе!"
