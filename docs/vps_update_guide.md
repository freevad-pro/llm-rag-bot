# 🚀 Инструкция по обновлению бота на VPS

Подробное руководство по обновлению Telegram бота на VPS сервере. Все команды можно копировать и вставлять в терминал.

---

## 📋 Содержание

1. [Быстрая проверка статуса](#быстрая-проверка-статуса)
2. [Вариант 1: Обычное обновление (сохранение локальных файлов)](#вариант-1-обычное-обновление)
3. [Вариант 2: Жесткое обновление (перезапись всех файлов)](#вариант-2-жесткое-обновление)
4. [Проверка после обновления](#проверка-после-обновления)
5. [Устранение проблем](#устранение-проблем)

---

## 🔍 Быстрая проверка статуса

Подключитесь к VPS и проверьте текущий статус:

```bash
# Подключение к VPS (замените на ваши данные)
ssh root@ваш-сервер.ru

# Переход в директорию проекта
cd /opt/llm-bot/app

# Проверка статуса контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверка последних логов бота
docker-compose -f docker-compose.prod.yml logs bot --tail=20
```

**🟢 Все работает если:**
- Контейнер `bot` в статусе `Up`
- В логах есть записи о запуске бота и нет критических ошибок

---

## 📥 Вариант 1: Обычное обновление

**Когда использовать:** Когда на сервере НЕТ локальных изменений или они нужны.

### Шаг 1: Проверка изменений

```bash
cd /opt/llm-bot/app
git status
```

**Если есть изменения** - решите:
- Сохранить их → используйте этот вариант
- Удалить их → переходите к [Варианту 2](#вариант-2-жесткое-обновление)

### Шаг 2: Загрузка обновлений

```bash
# Загрузка обновлений с GitHub
git fetch origin main

# Проверка что будет обновлено
git log HEAD..origin/main --oneline

# Применение обновлений
git pull origin main
```

**Если возникла ошибка слияния:**
```bash
# Прервать слияние и перейти к варианту 2
git merge --abort
```

### Шаг 3: Перезапуск бота

```bash
# Перезапуск только бота (быстро)
docker-compose -f docker-compose.prod.yml restart bot

# ИЛИ полная пересборка если были изменения в коде (медленно)
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache bot
docker-compose -f docker-compose.prod.yml up -d
```

**Используйте полную пересборку если:**
- Обновлялись Python файлы
- Менялись зависимости
- Добавлялись новые функции

---

## 🔥 Вариант 2: Жесткое обновление

**Когда использовать:** Когда есть конфликты, нужна точная копия репозитория или после критических изменений.

### Шаг 1: Остановка контейнеров

```bash
cd /opt/llm-bot/app

# Полная остановка всех контейнеров
docker-compose -f docker-compose.prod.yml down
```

### Шаг 2: Жесткая перезапись файлов

```bash
# ВНИМАНИЕ: Удалит ВСЕ локальные изменения!
git reset --hard HEAD
git clean -fd
git pull origin main --force
```

### Шаг 3: Полная пересборка

```bash
# Пересборка всех контейнеров
docker-compose -f docker-compose.prod.yml build --no-cache

# Запуск контейнеров
docker-compose -f docker-compose.prod.yml up -d
```

---

## ✅ Проверка после обновления

### 1. Проверка статуса контейнеров

```bash
# Статус всех контейнеров
docker-compose -f docker-compose.prod.yml ps

# Ожидаемый результат:
# ✅ app: Up (порт 8000)
# ✅ bot: Up  
# ✅ postgres: Up (healthy)
```

### 2. Проверка логов бота

```bash
# Последние 30 записей логов бота
docker-compose -f docker-compose.prod.yml logs bot --tail=30 -f
```

**🟢 Норма - должно быть:**
```
✅ Запуск Telegram бота...
✅ База данных инициализирована  
✅ Бот запущен: @ваш_бот
✅ Dispatcher настроен с поддержкой поиска, LLM...
✅ Запущен монитор неактивных пользователей
```

**🔴 Ошибки - НЕ должно быть:**
```
❌ BOT_TOKEN не настроен!
❌ TelegramConflictError: terminated by other getUpdates
❌ Failed to connect to database
❌ Critical error in...
```

### 3. Проверка работы бота

Отправьте боту в Telegram:
```
/start
```

**Ожидаемый результат:**
- Бот отвечает приветственным сообщением
- Показывается меню с кнопками
- В логах появляется `Новый чат: XXXXX`

### 4. Проверка health endpoint

```bash
# Проверка API
curl -s http://localhost:8000/health | jq
```

**Ожидаемый результат:**
```json
{
  "status": "healthy",
  "database": "connected",
  "bot": "running"
}
```

---

## 🚨 Устранение проблем

### Проблема: Бот не отвечает

**Диагностика:**
```bash
# Проверка статуса контейнера
docker-compose -f docker-compose.prod.yml ps bot

# Детальные логи
docker-compose -f docker-compose.prod.yml logs bot --tail=50
```

**Решение:**
```bash
# Перезапуск бота
docker-compose -f docker-compose.prod.yml restart bot

# Если не помогло - полная пересборка
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache bot
docker-compose -f docker-compose.prod.yml up -d bot
```

### Проблема: Ошибки базы данных

**Диагностика:**
```bash
# Проверка статуса PostgreSQL
docker-compose -f docker-compose.prod.yml ps postgres
docker-compose -f docker-compose.prod.yml logs postgres --tail=20
```

**Решение:**
```bash
# Перезапуск базы данных
docker-compose -f docker-compose.prod.yml restart postgres

# Ждем 10 секунд, затем перезапускаем бота
sleep 10
docker-compose -f docker-compose.prod.yml restart bot
```

### Проблема: Конфликт экземпляров бота

**Симптомы:** В логах `TelegramConflictError: terminated by other getUpdates`

**Решение:**
```bash
# Убить все процессы Python
pkill -f "main.py"

# Остановить все контейнеры с ботом
docker stop $(docker ps -q --filter "name=bot")

# Запустить только production версию
cd /opt/llm-bot/app
docker-compose -f docker-compose.prod.yml up -d bot
```

### Проблема: Нет места на диске

**Диагностика:**
```bash
df -h
docker system df
```

**Решение:**
```bash
# Очистка Docker кэша
docker system prune -f

# Удаление старых образов
docker image prune -a -f

# Очистка логов
docker-compose -f docker-compose.prod.yml logs --tail=0 > /dev/null
```

---

## 📞 Экстренные контакты

**При критических проблемах:**

1. **Быстрый откат:**
   ```bash
   cd /opt/llm-bot/app
   git log --oneline -5
   git reset --hard ПРЕДЫДУЩИЙ_КОММИТ
   docker-compose -f docker-compose.prod.yml restart bot
   ```

2. **Полная остановка:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

3. **Проверка ресурсов:**
   ```bash
   htop
   df -h
   free -h
   ```

---

## 💡 Полезные команды

```bash
# Мониторинг логов в реальном времени
docker-compose -f docker-compose.prod.yml logs bot -f

# Вход в контейнер бота для отладки
docker-compose -f docker-compose.prod.yml exec bot bash

# Проверка переменных окружения
docker-compose -f docker-compose.prod.yml exec bot env | grep BOT

# Просмотр текущей версии кода
git log --oneline -3

# Размер логов Docker
docker-compose -f docker-compose.prod.yml logs bot 2>/dev/null | wc -l
```

---

## ⚡ Чек-лист быстрого обновления

- [ ] `cd /opt/llm-bot/app`
- [ ] `git pull origin main`
- [ ] `docker-compose -f docker-compose.prod.yml restart bot`
- [ ] `docker-compose -f docker-compose.prod.yml logs bot --tail=10`
- [ ] Тест `/start` в Telegram
- [ ] ✅ Готово!

---

*Создано: 2025-09-14*  
*Версия: 1.0*
