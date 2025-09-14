# 🧪 Локальное тестирование ИИ-бота

Полноценная система локального тестирования для отладки перед деплоем в production.

## 🎯 Цели локального тестирования

- ✅ **Быстрая отладка** - тестируем изменения мгновенно
- ✅ **Изоляция** - не влияем на production среду  
- ✅ **Интеграция** - тестируем с реальными сервисами
- ✅ **E2E сценарии** - полные пользовательские потоки
- ✅ **Откат изменений** - легко вернуться к рабочей версии

## 🚀 Быстрый старт

### Windows (PowerShell)
```powershell
# 1. Настроить тестовую среду
.\scripts\test_local.ps1 setup

# 2. Запустить тесты
.\scripts\test_local.ps1 start
.\scripts\test_local.ps1 test

# 3. Проверить результат
.\scripts\test_local.ps1 status
```

### Linux/Mac (Bash) 
```bash
# 1. Настроить тестовую среду
./scripts/test_local.sh setup

# 2. Запустить тесты  
./scripts/test_local.sh start
./scripts/test_local.sh test

# 3. Проверить результат
./scripts/test_local.sh status
```

### Make (универсально)
```bash
# Быстрые команды через Makefile
make setup         # Настроить все
make test-local     # Запустить тестовую среду
make test           # Запустить тесты
make check          # Полная проверка
```

## 🐳 Архитектура тестовой среды

### Компоненты
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   App-Test      │    │   Bot-Test      │    │ PostgreSQL-Test │
│   Port: 8001    │    │  (Background)   │    │   Port: 5433    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Pytest-Runner  │
                    │  (On-demand)    │
                    └─────────────────┘
```

### Отличия от Production
| Аспект | Production | Local Test |
|---------|------------|------------|
| **Порт приложения** | 8000 | 8001 |
| **Порт БД** | 5432 (внутренний) | 5433 |
| **База данных** | Персистентная | Тестовая |
| **Данные** | Реальные | Тестовые |
| **Hot Reload** | ❌ | ✅ |
| **Debug режим** | ❌ | ✅ |

## 📋 Команды тестирования

### Управление средой
```bash
# Настройка (выполнить один раз)
make setup
./scripts/test_local.sh setup

# Запуск тестовой среды
make test-local
./scripts/test_local.sh start

# Остановка среды
./scripts/test_local.sh stop

# Полная очистка
./scripts/test_local.sh clean
```

### Запуск тестов
```bash
# Все тесты
make test
./scripts/test_local.sh test

# По типам
./scripts/test_local.sh test-unit    # Unit тесты (быстро)
./scripts/test_local.sh test-int     # Интеграционные
./scripts/test_local.sh test-e2e     # E2E тесты (медленно)

# С покрытием кода
make coverage
./scripts/test_local.sh coverage

# В режиме наблюдения (автоперезапуск)
make watch
./scripts/test_local.sh test-watch
```

### Качество кода
```bash
# Проверка стиля
make lint
./scripts/test_local.sh lint

# Автоформатирование
make format
./scripts/test_local.sh format

# Быстрая проверка (lint + unit тесты)
make check
./scripts/test_local.sh check
```

### Отладка
```bash
# Интерактивная оболочка в контейнере
./scripts/test_local.sh shell

# Подключение к тестовой БД
./scripts/test_local.sh db-shell

# Логи приложения
./scripts/test_local.sh logs app-test

# Статус всех сервисов
./scripts/test_local.sh status
```

## 🔧 Конфигурация

### Переменные окружения (.env.test)
```env
DEBUG=true
ENVIRONMENT=test
DATABASE_URL=postgresql+asyncpg://test_user:test_pass@localhost:5433/test_catalog_db
BOT_TOKEN=test_bot_token_for_local_testing
DEFAULT_LLM_PROVIDER=test
LEAD_INACTIVITY_THRESHOLD=1
```

### Тестовые данные
Автоматически создаются при запуске:
- **Пользователь**: `chat_id=999999`, `test_user`
- **LLM настройки**: тестовый провайдер
- **База данных**: чистая PostgreSQL с миграциями

## 🧬 Моки и фикстуры

### LLM провайдер
```python
# В тестах используется MockLLMProvider
mock_llm = MockLLMProvider()
mock_llm.set_responses([
    "Здравствуйте! Чем могу помочь?",
    "Найдено 5 товаров по вашему запросу..."
])
```

### Telegram уведомления
```python
# Все уведомления сохраняются для проверки
mock_notifier = MockTelegramNotifier()
# После теста проверяем:
assert len(mock_notifier.sent_notifications) == 1
```

### CRM интеграция
```python
# Можно настроить на успех или ошибку
mock_crm = MockCRMService()
mock_crm.set_failure(True, "Test CRM error")
```

## 📊 Отчеты

### Покрытие кода
После `make coverage`:
- **HTML отчет**: `htmlcov/index.html`
- **Консольный**: показывается автоматически

### Результаты тестов
- **JUnit XML**: `test-results/results.xml`
- **Подробные логи**: в консоли

## 🔄 Рабочий процесс

### Разработка новой функции
```bash
# 1. Настроить среду (один раз)
make setup

# 2. Запустить тестовую среду
make test-local

# 3. Разработка с автотестами
make watch  # Тесты перезапускаются при изменениях

# 4. Проверка перед коммитом
make check

# 5. Деплой если все ОК
make deploy
```

### Отладка проблемы
```bash
# 1. Запустить нужные тесты
./scripts/test_local.sh test -k "test_lead_creation"

# 2. Посмотреть логи
./scripts/test_local.sh logs

# 3. Подключиться к контейнеру
./scripts/test_local.sh shell

# 4. Проверить БД
./scripts/test_local.sh db-shell
```

## 🚨 Troubleshooting

### Частые проблемы

#### "Port already in use"
```bash
# Остановить все
./scripts/test_local.sh stop

# Если не помогло - принудительно
docker compose -f docker-compose.test.yml down
```

#### "Database connection failed"  
```bash
# Пересоздать БД
./scripts/test_local.sh clean
./scripts/test_local.sh setup
```

#### "Tests fail with import errors"
```bash
# Пересобрать образы
./scripts/test_local.sh clean
docker compose -f docker-compose.test.yml build --no-cache
```

#### "Hot reload doesn't work"
Проверьте volume маппинг в `docker-compose.test.yml`:
```yaml
volumes:
  - ./src:/app/src  # Должен быть примонтирован
```

### Проверка среды
```bash
# Статус всех контейнеров
docker compose -f docker-compose.test.yml ps

# Проверка доступности
curl http://localhost:8001/health

# Логи при старте
docker compose -f docker-compose.test.yml logs app-test
```

## 🔗 Интеграция с IDE

### VS Code
```json
// .vscode/tasks.json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Test Local",
            "type": "shell",
            "command": "./scripts/test_local.sh test",
            "group": "test"
        }
    ]
}
```

### PyCharm
- **Run Configuration**: External Tool
- **Program**: `./scripts/test_local.sh`
- **Arguments**: `test`

## 📚 Дополнительные возможности

### Профилирование тестов
```bash
# Показать самые медленные тесты
./scripts/test_local.sh test --durations=10

# Только быстрые тесты (< 1 сек)
./scripts/test_local.sh test -m "not slow"
```

### Параллельное выполнение
```bash
# Запуск тестов в нескольких процессах
./scripts/test_local.sh test -n auto
```

### Кастомные маркеры
```bash
# Только тесты базы данных
./scripts/test_local.sh test -m db

# Все кроме E2E
./scripts/test_local.sh test -m "not e2e"
```

---

**Принцип:** Тестируй локально, деплой уверенно! 🧪✅
