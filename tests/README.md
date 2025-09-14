# 🧪 Тестирование ИИ-бота

Комплексная система тестирования для ИИ-бота с поддержкой всех компонентов системы.

## 📁 Структура тестов

```
tests/
├── conftest.py              # Общие fixtures и настройки
├── fixtures/                # Фабрики тестовых данных
│   └── factories.py         # Factory Boy фабрики
├── unit/                    # Unit тесты (быстрые)
│   ├── test_lead_validation.py
│   └── test_catalog_components.py    # Тесты компонентов каталога
├── integration/             # Интеграционные тесты 
│   ├── test_database_operations.py
│   └── test_catalog_search.py       # Тесты поиска с Chroma DB
└── e2e/                     # End-to-end тесты (медленные)
    ├── test_telegram_scenarios.py
    └── test_catalog_user_scenarios.py # Полные сценарии каталога
```

## 🚀 Быстрый старт

### Установка зависимостей
```bash
poetry install  # Устанавливает все dev зависимости включая pytest
```

### Запуск тестов
```bash
# Все тесты
./scripts/run_tests.sh

# Только быстрые тесты
./scripts/run_tests.sh fast

# С покрытием кода
./scripts/run_tests.sh coverage

# Конкретный тип тестов
./scripts/run_tests.sh unit
./scripts/run_tests.sh integration
./scripts/run_tests.sh e2e
```

### Через bot команду (на VPS)
```bash
bot test           # Все тесты
bot test-fast      # Быстрые тесты
bot test-coverage  # С покрытием
```

## 📊 Типы тестов

### Unit тесты (⚡ быстрые)
- **Что тестируют:** Отдельные функции и классы
- **Скорость:** < 1 секунды на тест
- **Маркер:** `@pytest.mark.unit`

```python
def test_phone_validation():
    """Тест валидации телефона"""
    lead = LeadCreateRequest(
        name="Тест",
        phone="+79001234567",
        lead_source=LeadSource.TELEGRAM_BOT
    )
    assert lead.phone == "+79001234567"
```

### Integration тесты (🔗 средние)
- **Что тестируют:** Взаимодействие компонентов
- **Скорость:** 1-10 секунд на тест  
- **Маркер:** `@pytest.mark.integration`

```python
@pytest.mark.integration
async def test_lead_service_database(test_session):
    """Тест создания лида через сервис в БД"""
    lead_service = LeadService()
    created_lead = await lead_service.create_lead(...)
    assert created_lead.status == LeadStatus.PENDING_SYNC
```

### E2E тесты (🎯 полные сценарии)
- **Что тестируют:** Полные пользовательские сценарии
- **Скорость:** 10+ секунд на тест
- **Маркер:** `@pytest.mark.e2e`

```python
@pytest.mark.e2e
async def test_complete_user_journey(test_session):
    """Тест полного пути пользователя от старта до лида"""
    # 1. Пользователь запускает бота
    # 2. Ищет товары
    # 3. Заполняет форму контакта
    # 4. Создается лид
```

## 🏷️ Маркеры тестов

### По скорости
- `unit` - Быстрые unit тесты
- `integration` - Интеграционные тесты
- `e2e` - End-to-end тесты
- `slow` - Медленные тесты (> 1 секунды)

### По компонентам
- `db` - Тесты базы данных
- `api` - Тесты API endpoints
- `telegram` - Тесты Telegram бота
- `llm` - Тесты LLM провайдеров
- `search` - Тесты поиска товаров (каталог)
- `leads` - Тесты управления лидами

### Примеры запуска по маркерам
```bash
# Только тесты базы данных
pytest -m db

# Только быстрые тесты без медленных
pytest -m "unit or (integration and not slow)"

# Только тесты каталога и поиска
pytest -m search

# Быстрые тесты каталога (unit)
pytest -m "search and unit"

# Полные E2E тесты каталога
pytest -m "search and e2e"

# Только тесты Telegram
pytest -m telegram

# Все кроме E2E
pytest -m "not e2e"
```

## 🧬 Фабрики тестовых данных

Используем Factory Boy для создания тестовых данных:

```python
from tests.fixtures.factories import UserFactory, LeadFactory, TestDataBuilder

# Создание отдельных объектов
user = UserFactory()
lead = LeadFactory(user_id=user.id)

# Создание связанных данных
user, conversation = TestDataBuilder.create_user_with_conversation()
user, conv, messages = TestDataBuilder.create_full_dialog(messages_count=10)
```

## 📈 Покрытие кода

### Запуск с покрытием
```bash
./scripts/run_tests.sh coverage
```

### Просмотр отчета
- **HTML:** `htmlcov/index.html`
- **Терминал:** Показывается автоматически

### Целевые показатели
- **Unit тесты:** > 90% покрытие
- **Интеграционные:** > 80% покрытие
- **Общее покрытие:** > 85%

## 🔄 Автоматизация

### Pre-commit хуки
```bash
# Установка pre-commit
pre-commit install

# Ручной запуск всех проверок
pre-commit run --all-files
```

### CI/CD интеграция
Тесты автоматически запускаются:
- При коммите (через pre-commit)
- Перед деплоем (через `test_and_deploy.sh`)
- При обновлении (опционально в `update.sh`)

### Деплой с тестированием
```bash
# Полный цикл: тесты + деплой
./scripts/test_and_deploy.sh
```

## 🛠️ Настройка тестовой среды

### Переменные окружения для тестов
```bash
# В тестах используется in-memory SQLite
TEST_DATABASE_URL="sqlite+aiosqlite:///:memory:"

# Мокируются внешние сервисы
BOT_TOKEN="test_token"
LLM_PROVIDER="test"
```

### Фикстуры
- `test_session` - Тестовая сессия БД (откат после каждого теста)
- `test_client` - Синхронный HTTP клиент для FastAPI
- `async_client` - Асинхронный HTTP клиент

## 🔍 Тесты системы каталога

### Трехуровневая архитектура тестов каталога:

#### 🏃‍♂️ Unit тесты (`tests/unit/test_catalog_components.py`)
- **Скорость:** < 1 секунды
- **Что тестируют:** 
  - Создание и валидация `Product` объектов
  - `ExcelCatalogLoader` с моками
  - `SentenceTransformersEmbeddingFunction` с моками
- **Запуск:** `pytest -m "search and unit"`

#### 🔗 Integration тесты (`tests/integration/test_catalog_search.py`)
- **Скорость:** 1-10 секунд
- **Что тестируют:**
  - Реальную работу с Chroma DB
  - Загрузку Excel файлов 
  - Семантический поиск на разных языках
  - Качество результатов поиска
- **Запуск:** `pytest -m "search and integration"`

#### 🎯 E2E тесты (`tests/e2e/test_catalog_user_scenarios.py`)
- **Скорость:** 10+ секунд
- **Что тестируют:**
  - Полные пользовательские сценарии
  - Blue-green deployment (переиндексация)
  - Многоязычный поиск высокого качества
  - Производительность с большими каталогами
- **Запуск:** `pytest -m "search and e2e"`

### Быстрые команды для каталога:
```bash
# Все тесты каталога
pytest -m search

# Только быстрые тесты каталога  
pytest -m "search and unit"

# Полное тестирование каталога
pytest -m "search and (integration or e2e)"

# Тесты без медленных E2E
pytest -m "search and not e2e"
```

## 📋 Checklist для новых тестов

### При добавлении нового компонента:
- [ ] Unit тесты для всех публичных методов
- [ ] Integration тесты для взаимодействия с БД/API
- [ ] E2E тест основного сценария использования
- [ ] Обновить маркеры pytest
- [ ] Проверить покрытие кода

### При изменении существующего кода:
- [ ] Запустить связанные тесты
- [ ] Обновить тесты если изменилась логика
- [ ] Проверить что coverage не упало
- [ ] Запустить полный набор тестов перед коммитом

## 🚨 Troubleshooting

### Частые проблемы

#### Тесты БД не работают
```bash
# Проверить что pytest-asyncio установлен
poetry install

# Убедиться что используется test_session fixture
async def test_my_function(test_session):
    # ...
```

#### Медленные тесты
```bash
# Запуск только быстрых тестов
pytest -m "not slow"

# Параллельный запуск
pytest -n auto
```

#### Падают E2E тесты
```bash
# Подробный вывод для отладки
pytest -v -s tests/e2e/

# Остановка на первой ошибке
pytest -x tests/e2e/
```

## 📚 Полезные ресурсы

- [Pytest документация](https://docs.pytest.org/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Принцип:** Каждое изменение кода должно быть покрыто тестами! 🧪✅
