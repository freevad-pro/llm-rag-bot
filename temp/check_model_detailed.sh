#!/bin/bash
# Детальная проверка модели на сервере

echo "=== ПРОВЕРКА МОДЕЛИ ЭМБЕДДИНГОВ ==="

echo -e "\n1. Проверка директории кэша:"
docker compose -f docker-compose.prod.yml exec app bash -c "
if [ -d /root/.cache/torch/sentence_transformers ]; then
    echo '✅ Директория существует'
    ls -lah /root/.cache/torch/sentence_transformers/
else
    echo '❌ Директория НЕ существует'
fi
"

echo -e "\n2. Проверка файлов модели:"
docker compose -f docker-compose.prod.yml exec app bash -c "
MODEL_DIR='/root/.cache/torch/sentence_transformers/sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2'
if [ -d \"\$MODEL_DIR\" ]; then
    echo '✅ Директория модели существует'
    echo ''
    echo 'Список файлов:'
    ls -lh \"\$MODEL_DIR/\"
    echo ''
    echo 'Общий размер:'
    du -sh \"\$MODEL_DIR\"
else
    echo '❌ Директория модели НЕ существует'
fi
"

echo -e "\n3. Дата создания файлов (когда модель была скачана):"
docker compose -f docker-compose.prod.yml exec app bash -c "
MODEL_DIR='/root/.cache/torch/sentence_transformers/sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2'
if [ -d \"\$MODEL_DIR\" ]; then
    stat \"\$MODEL_DIR\" | grep -E 'Modify|Birth'
fi
"

echo -e "\n4. Проверка через Python API:"
docker compose -f docker-compose.prod.yml exec app python3 -c "
from pathlib import Path
import os

cache_dir = Path.home() / '.cache' / 'torch' / 'sentence_transformers'
model_name = 'sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2'
model_dir = cache_dir / model_name

if model_dir.exists():
    print('✅ Модель существует в кэше')
    
    # Подсчитываем размер
    total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
    print(f'Размер: {total_size / 1024 / 1024:.2f} MB')
    
    # Подсчитываем количество файлов
    file_count = len([f for f in model_dir.rglob('*') if f.is_file()])
    print(f'Файлов: {file_count}')
    
    # Проверяем основные файлы модели
    print('')
    print('Ключевые файлы:')
    key_files = ['config.json', 'pytorch_model.bin', 'model.safetensors', 'tokenizer_config.json']
    for key_file in key_files:
        file_path = model_dir / key_file
        if file_path.exists():
            size_mb = file_path.stat().st_size / 1024 / 1024
            print(f'  ✅ {key_file}: {size_mb:.2f} MB')
        else:
            print(f'  ❌ {key_file}: отсутствует')
else:
    print('❌ Модель НЕ найдена в кэше')
" 2>&1

echo -e "\n5. Тест работоспособности модели:"
docker compose -f docker-compose.prod.yml exec app python3 -c "
try:
    from sentence_transformers import SentenceTransformer
    import time
    
    print('Загружаем модель...')
    start = time.time()
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    load_time = time.time() - start
    
    print(f'⏱️  Время загрузки: {load_time:.2f} секунд')
    
    print('Тестируем эмбеддинги...')
    embedding = model.encode(['тестовая фраза'])
    
    print(f'✅ Модель работает!')
    print(f'Размерность эмбеддинга: {embedding.shape}')
except Exception as e:
    print(f'❌ Ошибка: {e}')
" 2>&1

echo -e "\n=== ПРОВЕРКА ЗАВЕРШЕНА ==="

