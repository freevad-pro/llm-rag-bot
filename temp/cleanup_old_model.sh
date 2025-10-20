#!/bin/bash
# Очистка старой модели из неправильного места и повторная загрузка

echo "=== Очистка старой модели и повторная загрузка ==="

echo -e "\n1. Проверяем где сейчас модель:"
docker compose -f docker-compose.prod.yml exec app ls -lh /root/.cache/ | grep models--

echo -e "\n2. Удаляем модель из неправильного места:"
docker compose -f docker-compose.prod.yml exec app rm -rf /root/.cache/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2
echo "   ✅ Удалено"

echo -e "\n3. Перезапускаем приложение:"
docker compose -f docker-compose.prod.yml restart app
echo "   ✅ Перезапущено"

echo -e "\n4. Проверяем структуру кэша:"
docker compose -f docker-compose.prod.yml exec app ls -lh /root/.cache/huggingface/

echo -e "\n=== Готово! ==="
echo "Теперь через UI загрузите модель заново."
echo "Она сохранится в правильное место: /root/.cache/huggingface/models--..."

