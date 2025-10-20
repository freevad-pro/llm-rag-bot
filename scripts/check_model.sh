#!/bin/bash
# Проверка статуса модели эмбеддингов на сервере

echo "=== Проверка модели эмбеддингов ==="

# Проверяем директорию с кэшем
echo -e "\n1. Проверка директории кэша:"
docker compose -f docker-compose.prod.yml exec app ls -lh /root/.cache/torch/sentence_transformers/ 2>/dev/null

if [ $? -ne 0 ]; then
    echo "   ❌ Директория не существует или пуста"
else
    echo "   ✅ Директория существует"
    
    # Показываем размер модели
    echo -e "\n2. Размер модели:"
    docker compose -f docker-compose.prod.yml exec app du -sh /root/.cache/torch/sentence_transformers/* 2>/dev/null
fi

# Проверяем через Python
echo -e "\n3. Проверка через API Python:"
docker compose -f docker-compose.prod.yml exec app python -c "
from pathlib import Path
cache_dir = Path.home() / '.cache' / 'torch' / 'sentence_transformers'
model_name = 'sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2'
model_dir = cache_dir / model_name

if model_dir.exists() and any(model_dir.iterdir()):
    print('   ✅ Модель загружена')
    total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
    print(f'   Размер: {total_size / 1024 / 1024:.2f} MB')
else:
    print('   ❌ Модель не загружена')
" 2>/dev/null

echo -e "\n=== Проверка завершена ==="

