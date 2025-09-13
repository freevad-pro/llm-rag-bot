#!/bin/bash
# Скрипт резервного копирования ИИ-бота
# Использование: ./scripts/backup.sh [--retention-days 30]

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

# Параметры по умолчанию
RETENTION_DAYS=30

# Обработка аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Использование: $0 [--retention-days N]"
            echo "  --retention-days N  Количество дней хранения backup'ов (по умолчанию: 30)"
            exit 1
            ;;
    esac
done

# Директории
BOT_DIR="/opt/llm-bot"
APP_DIR="$BOT_DIR/app"
DATA_DIR="$BOT_DIR/data"
CONFIG_DIR="$BOT_DIR/config"
BACKUP_DIR="$BOT_DIR/backups"

# Создаем директорию для backup'ов если её нет
mkdir -p $BACKUP_DIR

# Генерируем имя backup'а
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="llm-bot-backup-$DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

log "📦 Создаем backup: $BACKUP_NAME"

# Проверяем доступность сервисов
cd $APP_DIR
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    warning "⚠️  Сервисы не запущены. Backup будет создан из файлов на диске."
    DB_RUNNING=false
else
    DB_RUNNING=true
fi

# Создаем временную директорию для backup'а
mkdir -p $BACKUP_PATH

log "📊 Создаем backup базы данных PostgreSQL..."
if [ "$DB_RUNNING" = true ]; then
    # Создаем dump из запущенного контейнера
    docker-compose -f docker-compose.prod.yml exec -T postgres \
        pg_dump -U postgres -d catalog_db --no-owner --no-acl > $BACKUP_PATH/database.sql
    
    # Дополнительно создаем backup в формате custom для быстрого восстановления
    docker-compose -f docker-compose.prod.yml exec -T postgres \
        pg_dump -U postgres -d catalog_db -Fc > $BACKUP_PATH/database.dump
    
    success "✅ Backup БД создан (SQL и binary форматы)"
else
    # Если контейнер не запущен, копируем файлы данных
    if [ -d "$DATA_DIR/postgres" ] && [ "$(ls -A $DATA_DIR/postgres)" ]; then
        log "📁 Копируем файлы PostgreSQL..."
        cp -r $DATA_DIR/postgres $BACKUP_PATH/postgres_files
        success "✅ Файлы PostgreSQL скопированы"
    else
        warning "⚠️  Данные PostgreSQL не найдены"
    fi
fi

log "🧠 Создаем backup векторной базы Chroma..."
if [ -d "$DATA_DIR/chroma" ] && [ "$(ls -A $DATA_DIR/chroma)" ]; then
    cp -r $DATA_DIR/chroma $BACKUP_PATH/
    
    # Подсчитываем размер данных Chroma
    CHROMA_SIZE=$(du -sh $BACKUP_PATH/chroma | cut -f1)
    success "✅ Backup Chroma создан (размер: $CHROMA_SIZE)"
else
    warning "⚠️  Данные Chroma не найдены или пусты"
    mkdir -p $BACKUP_PATH/chroma
fi

log "📁 Создаем backup загруженных файлов..."
if [ -d "$DATA_DIR/uploads" ] && [ "$(ls -A $DATA_DIR/uploads)" ]; then
    cp -r $DATA_DIR/uploads $BACKUP_PATH/
    
    # Подсчитываем количество файлов
    FILE_COUNT=$(find $BACKUP_PATH/uploads -type f | wc -l)
    success "✅ Backup uploads создан ($FILE_COUNT файлов)"
else
    warning "⚠️  Загруженные файлы не найдены"
    mkdir -p $BACKUP_PATH/uploads
fi

log "⚙️ Создаем backup конфигурации..."
if [ -f "$CONFIG_DIR/.env" ]; then
    cp $CONFIG_DIR/.env $BACKUP_PATH/
    success "✅ Backup конфигурации создан"
else
    warning "⚠️  Файл конфигурации .env не найден"
fi

log "📋 Создаем backup логов (последние 7 дней)..."
LOG_COUNT=0
if [ -d "$DATA_DIR/logs" ]; then
    mkdir -p $BACKUP_PATH/logs
    
    # Копируем файлы логов не старше 7 дней
    find $DATA_DIR/logs -name "*.log" -mtime -7 -exec cp {} $BACKUP_PATH/logs/ \; 2>/dev/null || true
    
    # Копируем Docker логи если они есть
    if command -v docker > /dev/null && [ "$DB_RUNNING" = true ]; then
        docker-compose -f $APP_DIR/docker-compose.prod.yml logs --no-color > $BACKUP_PATH/logs/docker_logs_$DATE.log 2>/dev/null || true
    fi
    
    LOG_COUNT=$(find $BACKUP_PATH/logs -type f | wc -l)
    success "✅ Backup логов создан ($LOG_COUNT файлов)"
else
    warning "⚠️  Директория логов не найдена"
    mkdir -p $BACKUP_PATH/logs
fi

log "📝 Создаем метаданные backup'а..."
cat > $BACKUP_PATH/backup_info.txt << EOF
LLM Bot Backup Information
==========================
Дата создания: $(date)
Создан пользователем: $(whoami)
Хост: $(hostname)
Версия бота: $(cd $APP_DIR && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

Компоненты backup'а:
- База данных PostgreSQL: $([ -f "$BACKUP_PATH/database.sql" ] && echo "✅ Да" || echo "❌ Нет")
- Векторная БД Chroma: $([ -d "$BACKUP_PATH/chroma" ] && echo "✅ Да ($CHROMA_SIZE)" || echo "❌ Нет")
- Загруженные файлы: $([ -d "$BACKUP_PATH/uploads" ] && echo "✅ Да ($FILE_COUNT файлов)" || echo "❌ Нет")
- Конфигурация: $([ -f "$BACKUP_PATH/.env" ] && echo "✅ Да" || echo "❌ Нет")
- Логи: $([ -d "$BACKUP_PATH/logs" ] && echo "✅ Да ($LOG_COUNT файлов)" || echo "❌ Нет")

Для восстановления используйте:
./scripts/restore.sh $BACKUP_NAME

EOF

# Добавляем информацию о Git репозитории
if [ -d "$APP_DIR/.git" ]; then
    echo "Git информация:" >> $BACKUP_PATH/backup_info.txt
    echo "Коммит: $(cd $APP_DIR && git rev-parse HEAD)" >> $BACKUP_PATH/backup_info.txt
    echo "Ветка: $(cd $APP_DIR && git branch --show-current)" >> $BACKUP_PATH/backup_info.txt
    echo "Последний коммит: $(cd $APP_DIR && git log -1 --pretty=format:'%h %s (%an, %ad)' --date=short)" >> $BACKUP_PATH/backup_info.txt
fi

log "🗜️ Создаем архив..."
cd $BACKUP_DIR
tar -czf "${BACKUP_NAME}.tar.gz" $BACKUP_NAME/

# Получаем размер архива
ARCHIVE_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)

# Удаляем временную директорию
rm -rf $BACKUP_NAME/

success "✅ Архив создан: ${BACKUP_NAME}.tar.gz (размер: $ARCHIVE_SIZE)"

log "🧹 Очищаем старые backup'ы (старше $RETENTION_DAYS дней)..."
DELETED_COUNT=$(find $BACKUP_DIR -name "llm-bot-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ $DELETED_COUNT -gt 0 ]; then
    success "✅ Удалено старых backup'ов: $DELETED_COUNT"
else
    log "ℹ️  Старых backup'ов для удаления не найдено"
fi

# Показываем статистику backup'ов
log "📊 Статистика backup'ов:"
TOTAL_BACKUPS=$(find $BACKUP_DIR -name "llm-bot-backup-*.tar.gz" | wc -l)
TOTAL_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
echo "   Всего backup'ов: $TOTAL_BACKUPS"
echo "   Общий размер: $TOTAL_SIZE"
echo "   Последний backup: ${BACKUP_NAME}.tar.gz ($ARCHIVE_SIZE)"

# Проверяем свободное место на диске
DISK_USAGE=$(df $BACKUP_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    warning "⚠️  Внимание! Использование диска: $DISK_USAGE%. Рассмотрите уменьшение срока хранения backup'ов."
fi

# Создаем символическую ссылку на последний backup
ln -sf "${BACKUP_NAME}.tar.gz" "$BACKUP_DIR/latest.tar.gz"

success "🎉 Backup завершен успешно!"

echo
echo "=== ИНФОРМАЦИЯ О BACKUP'Е ==="
echo "📦 Файл: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "📏 Размер: $ARCHIVE_SIZE"
echo "📅 Создан: $(date)"
echo "🔗 Последний: $BACKUP_DIR/latest.tar.gz"
echo
echo "=== ВОССТАНОВЛЕНИЕ ==="
echo "Для восстановления выполните:"
echo "  cd /opt/llm-bot && tar -xzf backups/${BACKUP_NAME}.tar.gz"
echo "  ./scripts/restore.sh $BACKUP_NAME"
echo
echo "=== АВТОМАТИЗАЦИЯ ==="
echo "Для автоматических backup'ов добавьте в crontab:"
echo "  0 3 * * * $BOT_DIR/scripts/backup.sh >> $DATA_DIR/logs/backup.log 2>&1"
