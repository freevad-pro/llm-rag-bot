#!/bin/bash
# Проверка статуса модели эмбеддингов на сервере

echo "=== Проверка модели эмбеддингов ==="

# Проверяем директорию с кэшем HuggingFace
echo -e "\n1. Проверка директории кэша HuggingFace Hub:"
docker compose -f docker-compose.prod.yml exec app ls -lh /root/.cache/huggingface/hub/ 2>/dev/null

if [ $? -ne 0 ]; then
    echo "   ❌ Директория не существует или пуста"
else
    echo "   ✅ Директория существует"
    
    # Показываем размер модели
    echo -e "\n2. Размер модели:"
    docker compose -f docker-compose.prod.yml exec app du -sh /root/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2 2>/dev/null
fi

# Проверяем через Python
echo -e "\n3. Проверка через Python API:"
docker compose -f docker-compose.prod.yml exec app python -c "
from pathlib import Path
cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
model_name = 'models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2'
model_dir = cache_dir / model_name

if model_dir.exists() and any(model_dir.iterdir()):
    print('   ✅ Модель загружена')
    total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
    print(f'   Размер: {total_size / 1024 / 1024:.2f} MB')
else:
    print('   ❌ Модель не загружена')
" 2>/dev/null

# Тест работоспособности
echo -e "\n4. Тест работоспособности:"
docker compose -f docker-compose.prod.yml exec app python -c "
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    emb = model.encode(['тест'])
    print(f'   ✅ Модель работает! Размерность: {emb.shape}')
except Exception as e:
    print(f'   ❌ Ошибка: {e}')
" 2>/dev/null

echo -e "\n=== Проверка завершена ==="

