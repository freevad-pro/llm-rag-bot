#!/bin/bash
# Скрипт проверки и добавления новых переменных поиска
# Использование: ./scripts/check_env_search_settings.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[ENV CHECK]${NC} $1"
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

# Определяем файл конфигурации
if [ -f "/opt/llm-bot/config/.env" ]; then
    ENV_FILE="/opt/llm-bot/config/.env"
elif [ -f ".env" ]; then
    ENV_FILE=".env"
else
    error "Файл .env не найден!"
    exit 1
fi

log "Проверяем переменные поиска в файле: $ENV_FILE"

# Массив обязательных переменных поиска
declare -A SEARCH_VARS=(
    ["SEARCH_MIN_SCORE"]="0.45"
    ["SEARCH_NAME_BOOST"]="0.2"
    ["SEARCH_ARTICLE_BOOST"]="0.3"
    ["SEARCH_MAX_RESULTS"]="10"
)

MISSING_VARS=()
UPDATED=false

# Проверяем каждую переменную
for var_name in "${!SEARCH_VARS[@]}"; do
    default_value="${SEARCH_VARS[$var_name]}"
    
    if grep -q "^${var_name}=" "$ENV_FILE"; then
        current_value=$(grep "^${var_name}=" "$ENV_FILE" | cut -d'=' -f2)
        success "$var_name найдена (значение: $current_value)"
    else
        warning "$var_name отсутствует, будет добавлена со значением: $default_value"
        MISSING_VARS+=("$var_name=$default_value")
    fi
done

# Если есть отсутствующие переменные, добавляем их
if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log "Добавляем недостающие переменные поиска..."
    
    # Создаем backup
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    success "Backup создан: ${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Проверяем есть ли уже секция поиска
    if ! grep -q "НАСТРОЙКИ ПОИСКА" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# === НАСТРОЙКИ ПОИСКА ПО КАТАЛОГУ ===" >> "$ENV_FILE"
        echo "# Минимальный score для показа результатов (0.0-1.0)" >> "$ENV_FILE"
        echo "# Рекомендуется: 0.45 для высокого качества, 0.3 для большего охвата" >> "$ENV_FILE"
        echo "SEARCH_MIN_SCORE=0.45" >> "$ENV_FILE"
        echo "" >> "$ENV_FILE"
        echo "# Boost за совпадения в названии товара (0.0-0.5)" >> "$ENV_FILE"
        echo "# Рекомендуется: 0.2 для умеренного приоритета названию" >> "$ENV_FILE"
        echo "SEARCH_NAME_BOOST=0.2" >> "$ENV_FILE"
        echo "" >> "$ENV_FILE"
        echo "# Boost за совпадения в артикуле товара (0.0-0.5)" >> "$ENV_FILE"
        echo "# Рекомендуется: 0.3 (выше чем название) для точного поиска по артикулу" >> "$ENV_FILE"
        echo "SEARCH_ARTICLE_BOOST=0.3" >> "$ENV_FILE"
        echo "" >> "$ENV_FILE"
        echo "# Максимальное количество результатов поиска" >> "$ENV_FILE"
        echo "# Рекомендуется: 10 для оптимального UX, не более 20" >> "$ENV_FILE"
        echo "SEARCH_MAX_RESULTS=10" >> "$ENV_FILE"
        
        UPDATED=true
        success "Добавлены все переменные поиска с комментариями"
    else
        # Добавляем только отсутствующие переменные
        for var_setting in "${MISSING_VARS[@]}"; do
            echo "$var_setting" >> "$ENV_FILE"
            success "Добавлена переменная: $var_setting"
        done
        UPDATED=true
    fi
fi

if [ "$UPDATED" = true ]; then
    warning "Переменные окружения обновлены! Требуется перезапуск сервисов:"
    echo "  cd /opt/llm-bot && ./scripts/prod_restart.sh"
else
    success "Все переменные поиска присутствуют"
fi

# Показываем текущие значения
echo
log "Текущие настройки поиска:"
for var_name in "${!SEARCH_VARS[@]}"; do
    if grep -q "^${var_name}=" "$ENV_FILE"; then
        current_value=$(grep "^${var_name}=" "$ENV_FILE" | cut -d'=' -f2)
        echo "  $var_name = $current_value"
    fi
done

echo
log "Значения переменных поиска:"
echo "  SEARCH_MIN_SCORE: порог релевантности (0.0-1.0)"
echo "    0.3 = больше результатов, 0.6 = только очень релевантные"
echo "  SEARCH_NAME_BOOST: приоритет совпадениям в названии (0.0-0.5)"
echo "  SEARCH_ARTICLE_BOOST: приоритет совпадениям в артикуле (0.0-0.5)"
echo "  SEARCH_MAX_RESULTS: максимум результатов (рекомендуется 5-20)"
