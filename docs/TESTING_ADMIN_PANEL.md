# 🧪 Тестирование админ-панели локально

## 📋 Подготовка

### 1. Убедитесь что Docker запущен
```bash
# Проверить статус Docker
docker --version
docker-compose --version
```

### 2. Настройки уже готовы
- ✅ Файл `.env` создан из `env.test`
- ✅ Директории `data/persistent/chroma` и `data/uploads` созданы

## 🚀 Запуск системы

### 1. Остановите существующие контейнеры (если есть)
```bash
docker-compose down
```

### 2. Соберите и запустите контейнеры
```bash
# Сборка образа
docker-compose build app

# Запуск сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps
```

### 3. Дождитесь запуска (30-60 секунд)
```bash
# Проверка логов
docker-compose logs -f app

# Или отдельно PostgreSQL
docker-compose logs postgres
```

## 🧪 Тестирование

### 1. Проверьте health check
Откройте в браузере: http://localhost:8000/health

Должен вернуть JSON со статусом системы.

### 2. Создайте тестовых пользователей
```bash
# В отдельном терминале
python scripts/test_admin_panel.py
```

### 3. Откройте админ-панель
Браузер: **http://localhost:8000/admin/**

## 🎯 Что тестировать

### ✅ Страница авторизации (`/admin/login`)
- [x] Страница загружается без ошибок
- [x] Отображается форма для Telegram авторизации
- [x] Bootstrap стили применяются корректно
- [x] Адаптивность (измените размер окна)

### ✅ Без авторизации
- [x] Перенаправление с `/admin/` на `/admin/login`
- [x] API endpoints `/admin/api/*` возвращают 401

### ✅ Интерфейс (временно недоступен без реального Telegram)
- Для полного тестирования нужен реальный Telegram бот
- Замените в `.env` значения `ADMIN_TELEGRAM_IDS` на ваши реальные ID
- Добавьте реальный `BOT_TOKEN` от @BotFather

## 📊 Дополнительные endpoints

### API информация
- GET http://localhost:8000/ - Корневая страница
- GET http://localhost:8000/api/info - Информация о системе
- GET http://localhost:8000/docs - Swagger документация

### Админ API (требует авторизации)
- GET http://localhost:8000/admin/api/user-info - Информация о пользователе

## 🐛 Решение проблем

### Контейнеры не запускаются
```bash
# Посмотрите логи
docker-compose logs app
docker-compose logs postgres

# Пересоберите образы
docker-compose build --no-cache app
```

### База данных недоступна
```bash
# Проверьте PostgreSQL
docker-compose logs postgres

# Перезапустите только БД
docker-compose restart postgres
```

### Ошибки Python зависимостей
```bash
# Пересоберите с чистого листа
docker-compose down
docker system prune -f
docker-compose build --no-cache app
docker-compose up -d
```

### Порт 8000 занят
```bash
# Найдите процесс
netstat -ano | findstr :8000

# Или измените порт в docker-compose.yml
ports:
  - "8001:8000"  # Новый порт
```

## 🎉 Успешный результат

Если все работает правильно, вы увидите:

1. **Health check** возвращает статус "ok"
2. **Админ-панель** `/admin/login` загружается с красивым интерфейсом
3. **Bootstrap стили** применяются корректно
4. **Адаптивный дизайн** работает на мобильных
5. **Telegram Login Widget** отображается (но требует настоящего бота)

## 🚀 Следующие шаги

После успешного тестирования базового интерфейса можно переходить к:
- Реализации загрузки каталога
- Редактору промптов  
- Управлению услугами
- И других функций админ-панели

---

**Статус:** Базовая инфраструктура админ-панели готова к тестированию ✅


