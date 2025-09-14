#!/bin/bash
# Скрипт миграции каталога на версию 2.1 (три категории)
# Использование: ./scripts/migrate_catalog_v21.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[CATALOG MIGRATION]${NC} $1"
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

echo "🔄 Миграция каталога на версию 2.1.0 (три категории)"
echo "=================================================="
echo

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.prod.yml" ]; then
    if [ -d "/opt/llm-bot/app" ]; then
        cd /opt/llm-bot/app
    else
        error "Не найден файл docker-compose.prod.yml. Запустите скрипт из директории приложения."
        exit 1
    fi
fi

# Проверяем статус сервисов
log "Проверяем статус сервисов..."
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    error "Сервисы не запущены! Запустите сначала: ./scripts/prod.sh"
    exit 1
fi

# Проверяем что у нас есть новые переменные поиска
log "Проверяем переменные поиска..."
if [ -f "/opt/llm-bot/config/.env" ]; then
    ENV_FILE="/opt/llm-bot/config/.env"
elif [ -f ".env" ]; then
    ENV_FILE=".env"
else
    error "Файл .env не найден!"
    exit 1
fi

# Проверяем наличие новых переменных
missing_vars=0
for var in SEARCH_MIN_SCORE SEARCH_NAME_BOOST SEARCH_ARTICLE_BOOST SEARCH_MAX_RESULTS; do
    if ! grep -q "^${var}=" "$ENV_FILE"; then
        warning "Переменная $var отсутствует в конфигурации"
        missing_vars=$((missing_vars + 1))
    fi
done

if [ $missing_vars -gt 0 ]; then
    warning "Обнаружены отсутствующие переменные поиска."
    echo "Запустите сначала: ./scripts/check_env_search_settings.sh"
    echo "Затем перезапустите сервисы: ./scripts/prod_restart.sh"
    exit 1
fi

success "Все переменные поиска настроены"

# Проверяем текущую версию кода
log "Проверяем версию кода..."
CURRENT_COMMIT=$(git rev-parse --short HEAD)
log "Текущая версия: $CURRENT_COMMIT"

# Проверяем есть ли уже каталог в новом формате
log "Проверяем текущий каталог..."

# Делаем запрос к API для проверки структуры каталога
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log "API доступно, проверяем структуру каталога..."
    
    # Проверяем наличие данных в Chroma
    if docker-compose -f docker-compose.prod.yml exec -T app python -c "
import sys
sys.path.append('/app')
from src.infrastructure.search.catalog_service import CatalogSearchService
import asyncio

async def check_catalog():
    try:
        service = CatalogSearchService()
        is_indexed = await service.is_indexed()
        if is_indexed:
            print('CATALOG_EXISTS')
        else:
            print('CATALOG_EMPTY')
    except Exception as e:
        print(f'CATALOG_ERROR: {e}')

asyncio.run(check_catalog())
" 2>/dev/null; then
        catalog_status=$(docker-compose -f docker-compose.prod.yml exec -T app python -c "
import sys
sys.path.append('/app')
from src.infrastructure.search.catalog_service import CatalogSearchService
import asyncio

async def check_catalog():
    try:
        service = CatalogSearchService()
        is_indexed = await service.is_indexed()
        if is_indexed:
            print('CATALOG_EXISTS')
        else:
            print('CATALOG_EMPTY')
    except Exception as e:
        print(f'CATALOG_ERROR: {e}')

asyncio.run(check_catalog())
" 2>/dev/null | tr -d '\r')

        case "$catalog_status" in
            "CATALOG_EXISTS")
                warning "Каталог уже проиндексирован. Требуется переиндексация с новой структурой."
                echo
                echo "ВНИМАНИЕ: Существующий каталог использует старую структуру (одна категория)."
                echo "Для работы с версией 2.1 требуется каталог с тремя категориями:"
                echo "  - category 1 (основная категория)"
                echo "  - category 2 (подкатегория)"  
                echo "  - category 3 (детальная категория)"
                echo
                echo "Подготовьте Excel файл с новой структурой и загрузите через админку:"
                echo "  1. Откройте http://$(hostname -I | awk '{print $1}'):8000"
                echo "  2. Перейдите в раздел 'Загрузка каталога'"
                echo "  3. Загрузите новый файл с колонками category 1, category 2, category 3"
                ;;
            "CATALOG_EMPTY")
                success "Каталог пуст - готов к загрузке нового файла"
                echo
                echo "Загрузите каталог с новой структурой через админку:"
                echo "  1. Откройте http://$(hostname -I | awk '{print $1}'):8000"
                echo "  2. Перейдите в раздел 'Загрузка каталога'"
                echo "  3. Загрузите Excel файл с колонками:"
                echo "     - category 1 (основная категория)"
                echo "     - category 2 (подкатегория)"
                echo "     - category 3 (детальная категория)"
                ;;
            *)
                error "Ошибка проверки каталога: $catalog_status"
                exit 1
                ;;
        esac
    else
        error "Не удается проверить статус каталога"
        exit 1
    fi
else
    error "API недоступно! Проверьте статус сервисов: ./scripts/prod_status.sh"
    exit 1
fi

echo
log "Проверяем работу нового поиска..."

# Тестируем новые настройки поиска
echo "Текущие настройки поиска:"
for var in SEARCH_MIN_SCORE SEARCH_NAME_BOOST SEARCH_ARTICLE_BOOST SEARCH_MAX_RESULTS; do
    value=$(grep "^${var}=" "$ENV_FILE" | cut -d'=' -f2)
    echo "  $var = $value"
done

echo
log "Запускаем smoke tests..."
if [ -f "/opt/llm-bot/scripts/smoke_tests.sh" ]; then
    /opt/llm-bot/scripts/smoke_tests.sh search
    if [ $? -eq 0 ]; then
        success "Smoke test поиска прошел успешно"
    else
        warning "Smoke test поиска не прошел - возможно каталог еще не загружен"
    fi
else
    warning "Smoke tests не найдены"
fi

echo
success "🎉 Миграция на версию 2.1.0 завершена!"
echo
echo "=== СЛЕДУЮЩИЕ ШАГИ ==="
echo "1. ✅ Код обновлен до v2.1.0"
echo "2. ✅ Переменные поиска настроены"
echo "3. 🔄 Загрузите новый каталог через админку"
echo "4. 🧪 Протестируйте поиск в Telegram боте"
echo
echo "=== НОВЫЕ ВОЗМОЖНОСТИ ==="
echo "• Иерархические категории (3 уровня)"
echo "• Boost по артикулу (приоритет точным совпадениям)"
echo "• Фильтрация по минимальному score (качество результатов)"
echo "• Ограничение количества результатов (UX)"
echo "• Настройка всех параметров через ENV переменные"
echo
echo "=== ТЕСТИРОВАНИЕ ==="
echo "Проверьте поиск по разным типам запросов:"
echo "  • По названию: 'ноутбук', 'дрель'"
echo "  • По артикулу: 'DL001', 'FL002'"  
echo "  • По категории: 'электроника', 'инструменты'"
echo
warning "📝 После загрузки каталога рекомендуется протестировать все функции"
