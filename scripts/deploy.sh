#!/bin/bash
# Скрипт первичного деплоя ИИ-бота на VPS
# Использование: ./scripts/deploy.sh

set -e  # Выход при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
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

# Проверяем, что скрипт запущен не от root
if [ "$EUID" -eq 0 ]; then
    error "Не запускайте скрипт от root! Используйте обычного пользователя с sudo правами."
fi

# Проверяем наличие основных команд
command -v docker >/dev/null 2>&1 || error "Docker не установлен!"
command -v docker-compose >/dev/null 2>&1 || error "Docker Compose не установлен!"
command -v git >/dev/null 2>&1 || error "Git не установлен!"

log "🚀 Начинаем первичный деплой ИИ-бота..."

# Определяем директории
BOT_DIR="/opt/llm-bot"
APP_DIR="$BOT_DIR/app"
DATA_DIR="$BOT_DIR/data"
CONFIG_DIR="$BOT_DIR/config"
SCRIPTS_DIR="$BOT_DIR/scripts"

log "📁 Создаем структуру директорий..."

# Создаем основные директории
sudo mkdir -p $BOT_DIR/{app,data/{postgres,chroma,uploads,logs},config,scripts,backups}

# Устанавливаем права доступа
sudo chown -R $USER:$USER $BOT_DIR
chmod 755 $BOT_DIR

success "✅ Директории созданы"

# Проверяем, не клонирован ли уже репозиторий
if [ -d "$APP_DIR/.git" ]; then
    log "📥 Обновляем существующий репозиторий..."
    cd $APP_DIR
    git pull origin main
else
    log "📥 Клонируем репозиторий..."
    
    # Запрашиваем URL репозитория если он не задан
    if [ -z "$REPO_URL" ]; then
        echo -n "Введите URL вашего Git репозитория: "
        read REPO_URL
    fi
    
    if [ -z "$REPO_URL" ]; then
        error "URL репозитория не может быть пустым!"
    fi
    
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

success "✅ Код приложения получен"

log "⚙️ Настраиваем конфигурацию..."

# Проверяем наличие .env файла
if [ ! -f "$CONFIG_DIR/.env" ]; then
    if [ -f "$APP_DIR/env.production" ]; then
        log "📋 Перемещаем шаблон конфигурации в config/..."
        mv $APP_DIR/env.production $CONFIG_DIR/.env
        success "✅ Файл .env перемещен в $CONFIG_DIR/.env"
        warning "⚠️  ВАЖНО: Отредактируйте файл $CONFIG_DIR/.env и замените все PLACEHOLDER значения!"
        warning "⚠️  После редактирования запустите: $APP_DIR/scripts/deploy.sh"
        
        echo
        echo "Основные параметры для настройки:"
        echo "- BOT_TOKEN (от @BotFather)"
        echo "- POSTGRES_PASSWORD (сильный пароль для БД)"
        echo "- DEFAULT_LLM_PROVIDER (yandex или openai)"
        echo "- Соответствующие API ключи"
        echo "- MANAGER_TELEGRAM_CHAT_ID и ADMIN_TELEGRAM_IDS"
        echo
        
        exit 0
    else
        error "Файл env.production не найден в репозитории!"
    fi
fi

# Проверяем, что конфигурация настроена
if grep -q "ЗАМЕНИТЕ_НА_" "$CONFIG_DIR/.env"; then
    error "❌ В файле $CONFIG_DIR/.env остались не настроенные параметры! Отредактируйте файл и запустите скрипт заново."
fi

success "✅ Конфигурация настроена"

log "🏗️ Подготавливаем Docker Compose для production..."

# Копируем production конфигурацию если её нет
if [ ! -f "$APP_DIR/docker-compose.prod.yml" ]; then
    if [ -f "docker-compose.prod.yml" ]; then
        cp docker-compose.prod.yml $APP_DIR/
    else
        error "Файл docker-compose.prod.yml не найден!"
    fi
fi

# Проверяем конфигурацию Docker Compose
cd $APP_DIR
docker-compose -f docker-compose.prod.yml config > /dev/null
success "✅ Docker Compose конфигурация валидна"

log "📦 Создаем Docker образы..."
docker-compose -f docker-compose.prod.yml build

success "✅ Docker образы созданы"

log "🗄️ Запускаем PostgreSQL..."
docker-compose -f docker-compose.prod.yml up -d postgres

# Ждем готовности PostgreSQL
log "⏳ Ожидаем готовности PostgreSQL..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres -q; then
        success "✅ PostgreSQL готов"
        break
    fi
    if [ $i -eq 30 ]; then
        error "❌ PostgreSQL не стартовал за 30 секунд"
    fi
    sleep 1
done

log "🚀 Запускаем основное приложение..."
docker-compose -f docker-compose.prod.yml up -d app

# Ждем готовности приложения
log "⏳ Ожидаем готовности приложения..."
for i in {1..60}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "✅ Приложение готово"
        break
    fi
    if [ $i -eq 60 ]; then
        error "❌ Приложение не стартовало за 60 секунд. Проверьте логи: docker-compose -f docker-compose.prod.yml logs app"
    fi
    sleep 1
done

log "📋 Копируем скрипты управления..."
cp $APP_DIR/scripts/*.sh $SCRIPTS_DIR/
chmod +x $SCRIPTS_DIR/*.sh

log "⏰ Настраиваем cron задачи..."
# Добавляем backup задачу в crontab если её еще нет
if ! crontab -l 2>/dev/null | grep -q "$SCRIPTS_DIR/backup.sh"; then
    (crontab -l 2>/dev/null; echo "0 3 * * 0 $SCRIPTS_DIR/backup.sh >> $DATA_DIR/logs/backup.log 2>&1") | crontab -
    success "✅ Backup задача добавлена в cron (каждое воскресенье в 3:00)"
fi

log "🔍 Проверяем статус сервисов..."
docker-compose -f docker-compose.prod.yml ps

log "🧪 Тестируем основные функции..."

# Тест health endpoint
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    success "✅ Health check прошел"
else
    error "❌ Health check не прошел"
fi

# Проверяем подключение к БД
if docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT 1;" > /dev/null 2>&1; then
    success "✅ Подключение к БД работает"
else
    error "❌ Не удается подключиться к БД"
fi

success "🎉 Первичный деплой завершен успешно!"

echo
echo "=== ИНФОРМАЦИЯ О ДЕПЛОЕ ==="
echo "📁 Директория приложения: $APP_DIR"
echo "⚙️  Конфигурация: $CONFIG_DIR/.env"
echo "💾 Данные: $DATA_DIR"
echo "📜 Скрипты: $SCRIPTS_DIR"
echo
echo "=== ПОЛЕЗНЫЕ КОМАНДЫ ==="
echo "Просмотр логов: docker-compose -f $APP_DIR/docker-compose.prod.yml logs -f"
echo "Статус сервисов: docker-compose -f $APP_DIR/docker-compose.prod.yml ps"
echo "Обновление: $SCRIPTS_DIR/update.sh"
echo "Backup: $SCRIPTS_DIR/backup.sh"
echo "Перезапуск: docker-compose -f $APP_DIR/docker-compose.prod.yml restart"
echo
echo "=== СЛЕДУЮЩИЕ ШАГИ ==="
echo "1. Протестируйте бота в Telegram"
echo "2. Загрузите каталог товаров через админку: http://YOUR_SERVER_IP:8000"
echo "3. Настройте nginx для HTTPS (опционально)"
echo "4. Настройте мониторинг"
echo

warning "⚠️  Обязательно сохраните файл $CONFIG_DIR/.env - он содержит все пароли и ключи!"
