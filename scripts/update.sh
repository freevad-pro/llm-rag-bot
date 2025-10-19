#!/bin/bash
# Скрипт обновления ИИ-бота (Zero-downtime deployment)
# Использование: ./scripts/update.sh [--force]

set -e  # Выход при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для логирования
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

# Директории
BOT_DIR="/opt/llm-bot"
APP_DIR="$BOT_DIR/app"
DATA_DIR="$BOT_DIR/data"
SCRIPTS_DIR="$BOT_DIR/scripts"
BACKUP_DIR="$BOT_DIR/backups"

# Проверяем наличие необходимых файлов
[ ! -d "$APP_DIR" ] && error "Директория приложения $APP_DIR не найдена"
[ ! -f "$APP_DIR/docker-compose.prod.yml" ] && error "Файл docker-compose.prod.yml не найден"

log "🚀 Начинаем обновление ИИ-бота..."

cd $APP_DIR

# Проверяем текущий статус сервисов
log "🔍 Проверяем текущий статус..."
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    warning "Сервисы не запущены. Запускаем полный старт..."
    docker-compose -f docker-compose.prod.yml up -d
    exit 0
fi

# Проверяем наличие изменений в Git (если не принудительное обновление)
if [ "$1" != "--force" ] && [ "$1" != "--force-overwrite" ]; then
    log "📡 Проверяем наличие обновлений..."
    git fetch origin
    
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        log "ℹ️  Обновлений не найдено. Текущая версия актуальна."
        log "   Для принудительного обновления используйте:"
        log "   $0 --force              (сохранить локальные изменения)"
        log "   $0 --force-overwrite    (перезаписать локальные изменения)"
        exit 0
    fi
    
    log "📥 Найдены обновления. Получаем изменения..."
    git log --oneline HEAD..origin/main | head -10
    echo
fi

# Создаем backup перед обновлением
log "📦 Создаем backup перед обновлением..."
if [ -f "$SCRIPTS_DIR/backup.sh" ]; then
    $SCRIPTS_DIR/backup.sh
    success "✅ Backup создан"
else
    warning "⚠️  Скрипт backup.sh не найден, пропускаем создание backup"
fi

# Сохраняем информацию о текущем состоянии
CURRENT_COMMIT=$(git rev-parse HEAD)
CURRENT_IMAGE_ID=$(docker images --format "table {{.ID}}" | grep -v "IMAGE" | head -1)

log "📝 Текущая версия: $(git rev-parse --short HEAD)"
log "📝 Образ: $CURRENT_IMAGE_ID"

# Проверяем наличие локальных изменений
log "🔍 Проверяем локальные изменения..."
if ! git diff-index --quiet HEAD --; then
    warning "⚠️  Обнаружены локальные изменения в файлах:"
    git diff --name-only HEAD
    echo
    
    if [ "$1" = "--force-overwrite" ]; then
        warning "🔨 Режим принудительной перезаписи - сбрасываем локальные изменения..."
        git stash push -m "Auto-stash before force update $(date)" || true
        git reset --hard HEAD
    elif [ "$1" = "--force" ]; then
        log "💾 Сохраняем локальные изменения в stash..."
        git stash push -m "Auto-stash before update $(date)"
        success "✅ Локальные изменения сохранены в stash"
    else
        error "❌ Обнаружены локальные изменения. Используйте один из вариантов:
  $0              - безопасное обновление (остановится при конфликтах)
  $0 --force      - сохранить локальные изменения в stash и обновить
  $0 --force-overwrite - принудительно перезаписать все локальные изменения"
    fi
fi

# Получаем новый код
log "📥 Получаем обновления из Git..."
git pull origin main

NEW_COMMIT=$(git rev-parse HEAD)
log "📝 Новая версия: $(git rev-parse --short HEAD)"

# Проверяем, изменились ли файлы, требующие пересборки образа
REBUILD_NEEDED=false

if git diff --name-only $CURRENT_COMMIT $NEW_COMMIT | grep -qE "(Dockerfile|pyproject.toml|requirements.*\.txt)"; then
    log "🏗️ Обнаружены изменения в зависимостях, требуется пересборка образа..."
    REBUILD_NEEDED=true
fi

# Проверяем изменения в docker-compose.prod.yml
if git diff --name-only $CURRENT_COMMIT $NEW_COMMIT | grep -q "docker-compose.prod.yml"; then
    log "⚙️ Обнаружены изменения в Docker Compose конфигурации..."
    REBUILD_NEEDED=true
fi

# Если принудительное обновление - всегда пересобираем
if [ "$1" = "--force" ] || [ "$1" = "--force-overwrite" ]; then
    REBUILD_NEEDED=true
    log "🔨 Принудительное обновление - пересобираем образ..."
fi

# Проверяем валидность новой конфигурации
log "✅ Проверяем валидность новой конфигурации..."
if ! docker-compose -f docker-compose.prod.yml config > /dev/null; then
    error "❌ Новая конфигурация Docker Compose невалидна!"
fi

# Пересобираем образ если нужно
if [ "$REBUILD_NEEDED" = true ]; then
    log "🏗️ Собираем новый Docker образ..."
    docker-compose -f docker-compose.prod.yml build app
    success "✅ Новый образ собран"
else
    log "ℹ️  Пересборка образа не требуется"
fi

# Получаем ID нового образа
NEW_IMAGE_ID=$(docker images --format "table {{.ID}}" | grep -v "IMAGE" | head -1)

# Создаем функцию отката
rollback() {
    warning "🔄 Выполняем откат к предыдущей версии..."
    
    # Откатываем код
    git reset --hard $CURRENT_COMMIT
    
    # Останавливаем текущие контейнеры
    docker-compose -f docker-compose.prod.yml stop app
    
    # Если был собран новый образ, удаляем его и возвращаемся к старому
    if [ "$REBUILD_NEEDED" = true ] && [ "$NEW_IMAGE_ID" != "$CURRENT_IMAGE_ID" ]; then
        docker rmi $NEW_IMAGE_ID 2>/dev/null || true
        log "🏗️ Пересобираем предыдущую версию..."
        docker-compose -f docker-compose.prod.yml build app
    fi
    
    # Запускаем предыдущую версию
    docker-compose -f docker-compose.prod.yml up -d app
    
    error "❌ Откат выполнен. Проверьте логи и устраните проблемы."
}

# Обновляем только приложение (БД остается работать)
log "⏹️ Останавливаем приложение..."
docker-compose -f docker-compose.prod.yml stop app

log "▶️ Запускаем новую версию приложения..."
docker-compose -f docker-compose.prod.yml up -d app

# Запускаем миграции базы данных
log "🗃️ Применяем миграции базы данных..."
sleep 10  # Даем время контейнеру запуститься
if docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head; then
    success "✅ Миграции применены успешно"
else
    log "❌ Ошибка применения миграций"
    log "📋 Показываем статус миграций:"
    docker-compose -f docker-compose.prod.yml exec -T app alembic current || true
    log "📋 Показываем историю миграций:"
    docker-compose -f docker-compose.prod.yml exec -T app alembic history || true
    rollback
fi

# Ждем готовности нового контейнера
log "⏳ Ожидаем готовности нового контейнера..."
WAIT_TIME=60
for i in $(seq 1 $WAIT_TIME); do
    if docker-compose -f docker-compose.prod.yml ps app | grep -q "Up"; then
        log "📦 Контейнер запущен, проверяем health..."
        break
    fi
    
    if [ $i -eq $WAIT_TIME ]; then
        log "❌ Контейнер не запустился за $WAIT_TIME секунд"
        rollback
    fi
    
    sleep 1
done

# Проверяем health endpoint
log "🔍 Проверяем health endpoint..."
HEALTH_WAIT=30
for i in $(seq 1 $HEALTH_WAIT); do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "✅ Health check прошел"
        break
    fi
    
    if [ $i -eq $HEALTH_WAIT ]; then
        log "❌ Health check не прошел за $HEALTH_WAIT секунд"
        log "📋 Логи контейнера:"
        docker-compose -f docker-compose.prod.yml logs --tail=20 app
        rollback
    fi
    
    sleep 1
done

# Дополнительные проверки
log "🧪 Выполняем дополнительные проверки..."

# Проверяем подключение к БД
if ! docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT 1;" > /dev/null 2>&1; then
    error "❌ Не удается подключиться к БД после обновления"
    rollback
fi

# Проверяем работу Telegram бота (если настроен webhook endpoint)
if curl -f http://localhost:8000/webhook > /dev/null 2>&1; then
    success "✅ Webhook endpoint доступен"
fi

# Проверяем логи на критические ошибки
if docker-compose -f docker-compose.prod.yml logs --since=30s app | grep -i "CRITICAL\|FATAL\|ERROR" | grep -v "Health check"; then
    warning "⚠️  Обнаружены ошибки в логах приложения. Проверьте детали:"
    docker-compose -f docker-compose.prod.yml logs --tail=10 app
fi

success "✅ Все проверки пройдены"

# Очищаем старые образы
log "🧹 Очищаем старые Docker образы..."
if [ "$REBUILD_NEEDED" = true ]; then
    # Удаляем dangling образы (без тегов)
    docker image prune -f > /dev/null 2>&1 || true
    
    # Удаляем старые версии образов приложения (оставляем последние 3)
    docker images --format "table {{.ID}} {{.CreatedAt}}" | \
        grep -v "CREATED" | \
        sort -k2 -r | \
        tail -n +4 | \
        awk '{print $1}' | \
        xargs -r docker rmi > /dev/null 2>&1 || true
fi

# Обновляем скрипты управления
log "📜 Обновляем скрипты управления..."
if [ -d "scripts" ]; then
    # Создаем директорию если её нет
    mkdir -p $SCRIPTS_DIR
    
    cp scripts/*.sh $SCRIPTS_DIR/
    chmod +x $SCRIPTS_DIR/*.sh
    success "✅ Скрипты обновлены"
fi

# Финальная проверка статуса
log "📊 Проверяем итоговый статус сервисов..."
docker-compose -f docker-compose.prod.yml ps

success "🎉 Обновление завершено успешно!"

echo
echo "=== РЕЗУЛЬТАТ ОБНОВЛЕНИЯ ==="
echo "📝 Предыдущая версия: $(git rev-parse --short $CURRENT_COMMIT)"
echo "📝 Новая версия: $(git rev-parse --short $NEW_COMMIT)"
echo "🏗️ Образ пересобран: $([ "$REBUILD_NEEDED" = true ] && echo "Да" || echo "Нет")"
echo "⏱️  Время обновления: $(date)"
echo
echo "=== ИЗМЕНЕНИЯ ==="
git log --oneline $CURRENT_COMMIT..$NEW_COMMIT | head -10
echo
echo "=== ПОЛЕЗНЫЕ КОМАНДЫ ==="
echo "Просмотр логов: docker-compose -f $APP_DIR/docker-compose.prod.yml logs -f app"
echo "Статус сервисов: docker-compose -f $APP_DIR/docker-compose.prod.yml ps"
echo "Health check: curl http://localhost:8000/health"
echo
warning "📝 Рекомендуется протестировать основные функции бота после обновления"
