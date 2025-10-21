#!/bin/bash

# Скрипт очистки дискового пространства для LLM RAG Bot
# Удаляет временные коллекции ChromaDB и старые файлы

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Пути
CHROMA_DIR="/opt/llm-bot/data/chroma"
UPLOADS_DIR="/opt/llm-bot/data/uploads"
LOGS_DIR="/opt/llm-bot/logs"

echo -e "${BLUE}🧹 Скрипт очистки дискового пространства LLM RAG Bot${NC}"
echo "=================================================="

# Функция для безопасного удаления
safe_remove() {
    local path="$1"
    local description="$2"
    
    if [ -e "$path" ]; then
        echo -e "${YELLOW}Удаляем: $description${NC}"
        echo "  Путь: $path"
        
        # Показываем размер перед удалением
        if [ -d "$path" ]; then
            size=$(du -sh "$path" 2>/dev/null | cut -f1)
            echo "  Размер: $size"
        fi
        
        rm -rf "$path"
        echo -e "${GREEN}✅ Удалено успешно${NC}"
    else
        echo -e "${YELLOW}⚠️  Не найдено: $description${NC}"
    fi
    echo ""
}

# Функция для показа статистики
show_stats() {
    local title="$1"
    local path="$2"
    
    echo -e "${BLUE}📊 $title${NC}"
    if [ -d "$path" ]; then
        echo "  Путь: $path"
        echo "  Размер: $(du -sh "$path" 2>/dev/null | cut -f1)"
        echo "  Файлов/папок: $(find "$path" -type f 2>/dev/null | wc -l)"
    else
        echo "  Директория не существует"
    fi
    echo ""
}

echo -e "${BLUE}📊 Текущее состояние дискового пространства:${NC}"
echo "=================================================="

# Показываем статистику до очистки
show_stats "ChromaDB коллекции" "$CHROMA_DIR"
show_stats "Загруженные файлы" "$UPLOADS_DIR"
show_stats "Логи" "$LOGS_DIR"

# Общий размер данных
if [ -d "/opt/llm-bot/data" ]; then
    echo -e "${BLUE}📊 Общий размер данных:${NC}"
    du -sh /opt/llm-bot/data/
    echo ""
fi

echo -e "${YELLOW}🔍 Поиск временных и backup коллекций...${NC}"
echo "=================================================="

# Поиск временных коллекций ChromaDB
temp_collections=$(find "$CHROMA_DIR" -maxdepth 1 -type d -name "*temp*" 2>/dev/null || true)
backup_collections=$(find "$CHROMA_DIR" -maxdepth 1 -type d -name "*backup*" 2>/dev/null || true)

if [ -n "$temp_collections" ]; then
    echo -e "${RED}Найдены временные коллекции:${NC}"
    echo "$temp_collections"
    echo ""
else
    echo -e "${GREEN}✅ Временные коллекции не найдены${NC}"
fi

if [ -n "$backup_collections" ]; then
    echo -e "${RED}Найдены backup коллекции:${NC}"
    echo "$backup_collections"
    echo ""
else
    echo -e "${GREEN}✅ Backup коллекции не найдены${NC}"
fi

# Показываем все коллекции ChromaDB
echo -e "${BLUE}📋 Все коллекции ChromaDB:${NC}"
if [ -d "$CHROMA_DIR" ]; then
    ls -la "$CHROMA_DIR" | grep "^d" | awk '{print "  " $9 " (" $5 " байт)"}'
else
    echo "  Директория ChromaDB не найдена"
fi
echo ""

# Запрашиваем подтверждение
echo -e "${YELLOW}❓ Выполнить очистку? (y/N)${NC}"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧹 Начинаем очистку...${NC}"
    echo "=================================================="
    
    # Удаляем временные коллекции
    if [ -n "$temp_collections" ]; then
        echo "$temp_collections" | while read -r collection; do
            safe_remove "$collection" "Временная коллекция ChromaDB"
        done
    fi
    
    # Удаляем backup коллекции
    if [ -n "$backup_collections" ]; then
        echo "$backup_collections" | while read -r collection; do
            safe_remove "$collection" "Backup коллекция ChromaDB"
        done
    fi
    
    # Очистка старых логов (старше 30 дней)
    if [ -d "$LOGS_DIR" ]; then
        echo -e "${YELLOW}Очистка старых логов (старше 30 дней)...${NC}"
        find "$LOGS_DIR" -type f -name "*.log" -mtime +30 -delete 2>/dev/null || true
        echo -e "${GREEN}✅ Старые логи удалены${NC}"
        echo ""
    fi
    
    # Очистка временных файлов Python
    echo -e "${YELLOW}Очистка временных файлов Python...${NC}"
    find /opt/llm-bot -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find /opt/llm-bot -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ Временные файлы Python удалены${NC}"
    echo ""
    
    echo -e "${GREEN}🎉 Очистка завершена!${NC}"
    echo "=================================================="
    
    # Показываем статистику после очистки
    echo -e "${BLUE}📊 Состояние после очистки:${NC}"
    show_stats "ChromaDB коллекции" "$CHROMA_DIR"
    show_stats "Загруженные файлы" "$UPLOADS_DIR"
    show_stats "Логи" "$LOGS_DIR"
    
    # Общий размер данных после очистки
    if [ -d "/opt/llm-bot/data" ]; then
        echo -e "${BLUE}📊 Общий размер данных после очистки:${NC}"
        du -sh /opt/llm-bot/data/
    fi
    
else
    echo -e "${YELLOW}❌ Очистка отменена${NC}"
fi

echo ""
echo -e "${BLUE}💡 Рекомендации:${NC}"
echo "1. Регулярно запускайте этот скрипт для очистки"
echo "2. Мониторьте размер директории /opt/llm-bot/data/"
echo "3. При превышении 80% диска - удаляйте старые версии каталогов"
echo "4. Рассмотрите увеличение диска или настройку автоматической очистки"
