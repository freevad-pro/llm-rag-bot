# AI Агент для консультирования клиентов
## Архитектурная документация для Cursor v2.0

---

## 1. Обзор системы

### Назначение
AI-агент для консультирования по каталогу 40,000+ товаров, квалификации лидов и передачи менеджерам.

### Ключевые требования
- **Каналы**: Telegram бот + веб-виджет
- **Поиск**: товары (Chroma) + услуги компании (PostgreSQL)  
- **Мультиязычность**: автоматические ответы на языке пользователя
- **CRM**: Zoho с retry (макс 2 попытки)
- **Нагрузка**: до 100 одновременных пользователей
- **Время ответа**: < 2 секунды

---

## 2. Технологический стек

- **Python 3.11+** - основной язык
- **aiogram 3.x** - Telegram бот (полностью асинхронный)
- **FastAPI** - API + админка + WebSocket
- **Chroma** - векторный поиск товаров (персистентность на диске)
- **PostgreSQL 15** - услуги, пользователи, лиды, настройки
- **Docker Compose** - контейнеризация
- **LLM**: настраиваемый (OpenAI/YandexGPT через фабрику)

---

## 3. Архитектурные принципы

### Clean Architecture + Функциональный стиль
- **Классы**: сервисы, репозитории, конфигурация
- **Функции**: бизнес-логика, обработчики, трансформации  
- **DI везде**: все зависимости через конструктор
- **Type hints**: обязательно для всех функций и методов

### Структура проекта
```
src/
├── domain/           # Бизнес-логика без зависимостей
│   ├── entities/     # Dataclasses для сущностей
│   ├── services/     # Бизнес-сервисы (чистые функции)
│   └── interfaces/   # Протоколы и ABC
├── application/      # Use cases и координация
│   ├── telegram/     # Handlers, states, keyboards
│   ├── web/         # API endpoints, admin routes
│   └── shared/      # Общие use cases
├── infrastructure/   # Внешние сервисы
│   ├── database/    # PostgreSQL repositories
│   ├── search/      # Chroma + embeddings
│   ├── llm/         # LLM провайдеры
│   ├── crm/         # Zoho API
│   └── cache/       # TTLCache in-memory
└── presentation/    # UI слой
    ├── templates/   # Jinja2 + HTMX
    └── static/      # CSS, JS
```

---

## 4. Основные компоненты

### 4.1 Поиск по каталогу (Chroma)

**Принцип**: Каждая строка Excel = отдельный Document в Chroma

```python
class CatalogSearchService:
    """
    Использует:
    - SentenceTransformers: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
    - Chroma persist_directory: /app/data/chroma (cosine similarity)
    - Blue-green deployment при переиндексации
    - Boost система: приоритет артикулам и названиям
    - Фильтрация по минимальному score
    """
    
    async def index_catalog(excel_path: str) -> None:
        # Excel → Documents → Chroma
        # Metadata: id, name, category_1, category_2, category_3, article, photo_url
        
    async def search_products(query: str, k: int = 10) -> list[SearchResult]:
        # Семантический поиск с boost и фильтрацией
        # 1. Векторный поиск через Chroma (cosine similarity)
        # 2. Boost за совпадения в названии (SEARCH_NAME_BOOST)
        # 3. Boost за совпадения в артикуле (SEARCH_ARTICLE_BOOST)
        # 4. Фильтрация по минимальному score (SEARCH_MIN_SCORE)
        # 5. Ограничение результатов (SEARCH_MAX_RESULTS)
```

### 4.2 Классификация и маршрутизация запросов

```python
class QueryClassifier:
    """LLM определяет тип запроса: PRODUCT, SERVICE, GENERAL"""
    
class SearchOrchestrator:
    """
    Маршрутизация:
    - PRODUCT → CatalogSearchService (Chroma)
    - SERVICE → KnowledgeBaseService (PostgreSQL)  
    - GENERAL → базовый промпт LLM
    """
```

### 4.3 LLM с мультиязычностью

```python
class LLMService:
    """
    Системный промпт:
    - ВСЕГДА отвечать на языке пользователя
    - Консультировать по товарам и услугам
    - Собирать контакты заинтересованных
    """
    
class LLMProviderFactory:
    """Создает провайдера по настройке из БД: openai/yandex/anthropic"""
```

### 4.4 Управление диалогами

```python
class ConversationService:
    """
    - Сохраняет ВСЕ сообщения в PostgreSQL
    - В LLM отправляет последние 20 сообщений
    - Контекст включает историю + метаданные
    """
```

### 4.5 CRM интеграция с гарантией доставки

```python
class ZohoCRMService:
    """
    Retry логика:
    1. Сохранение в PostgreSQL (всегда успешно)
    2. Попытка отправки в Zoho
    3. При ошибке - retry через 30 мин (макс 2 раза)
    4. Уведомления на каждом этапе
    """
```

---

## 5. Схема базы данных

### Основные таблицы

```
users
- id: BIGSERIAL PK
- chat_id: BIGINT UNIQUE NOT NULL (основной идентификатор!)
- telegram_user_id, username, first_name, last_name
- phone, email
- created_at

company_services (услуги компании, НЕ товары)
- id, title, description, category
- keywords: TEXT[] (для улучшения поиска)
- active: BOOLEAN

leads
- id, user_id (FK users)
- name, phone (NOT NULL), email, question
- status: pending_sync|synced|failed
- sync_attempts: INTEGER (CHECK <= 2)
- zoho_lead_id, last_sync_attempt

conversations
- id, chat_id, user_id (FK)
- started_at, ended_at, platform, status
- metadata: JSONB

messages  
- id, conversation_id (FK)
- role: user|assistant|system
- content, created_at
- metadata: JSONB

llm_settings
- provider: openai|yandex|anthropic
- is_active, config: JSONB

prompts
- name (UNIQUE), content, version, active

system_logs
- level: ERROR|WARNING|CRITICAL|BUSINESS
- message, metadata: JSONB, created_at

usage_statistics (NEW!)
- provider: openai|yandexgpt
- model: gpt-4o-mini|gpt-4o|yandexgpt-lite
- year, month, total_tokens
- price_per_1k_tokens, currency
- created_at, updated_at

company_info (NEW!)
- filename, content_text, file_size
- is_active, version, created_at
```

### Важные индексы
- messages(conversation_id, created_at)
- leads(status, created_at)  
- logs(level, created_at DESC)

---

## 6. Паттерны и обработка ошибок

### 6.1 Обработка ошибок

```python
# Каждый слой имеет свои исключения
class DomainError(Exception): pass
class InfrastructureError(Exception): pass
class ValidationError(DomainError): pass

# Паттерн обработки
try:
    result = await service.process()
except ValidationError as e:
    # Вернуть пользователю понятную ошибку
except InfrastructureError as e:
    # Логировать, retry, fallback
except Exception as e:
    # Критическая ошибка → алерт админам
```

### 6.2 Логирование

```python
# Стратегия: критичное в БД, debug в файлы, алерты в Telegram
class HybridLogger:
    """
    - DEBUG → файлы (опционально)
    - ERROR, WARNING → PostgreSQL
    - CRITICAL → PostgreSQL + Telegram алерт
    - BUSINESS события → PostgreSQL для аналитики
    """
```

### 6.3 Валидация

```python
# Pydantic модели на всех границах
class LeadCreateRequest(BaseModel):
    last_name: str = Field(min_length=1, max_length=200)  # обязательное
    phone: str | None = Field(regex=r'^\+?[1-9]\d{1,14}$')
    email: EmailStr | None
    whatsapp: str | None  # копия телефона если есть
    company: str | None
    telegram: str | None
    lead_first_communication_channel: str = Field(regex=r'^(TG|SalesIQ Chat)$')
```

---

## 7. Deployment архитектура

### Контейнеры и персистентность

```
VPS структура:
- Docker контейнер #1: App (FastAPI сервер - API, админка, health checks)
- Docker контейнер #2: Bot (Telegram бот - отдельный процесс)
- Docker контейнер #3: PostgreSQL (никогда не трогается)
- Папка на диске: /data/persistent/chroma (векторная БД)

При деплое:
1. git pull
2. docker-compose build app bot
3. docker-compose up -d app bot --no-deps
Данные остаются на месте!

Разделение контейнеров:
- app: DISABLE_TELEGRAM_BOT=true (только FastAPI)
- bot: python -m src.main bot (только Telegram бот)
- postgres: изолированная база данных
```

### Docker volumes

```yaml
services:
  app:
    volumes:
      - ./data/persistent/chroma:/app/data/chroma  # Chroma БД
      - ./data/uploads:/app/data/uploads          # Excel файлы
      
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data    # Docker volume
```

---

## 8. Админ-панель

### Роли и права

| Функция | Менеджер | Админ |
|---------|----------|-------|
| Статистика + AI расходы | Базовая | Полная |
| Загрузка каталога | ✅ | ✅ |
| Редактирование промптов | ✅ | ✅ |
| Управление услугами | ✅ | ✅ |
| Загрузка "О компании" (DOCX) | ✅ | ✅ |
| Управление пользователями | ❌ | ✅ |
| Управление базой данных | ❌ | ✅ |
| Общие настройки системы | ❌ | ✅ |
| Статистика AI расходов | ❌ | ✅ |
| Просмотр логов | ❌ | ✅ |

### Технологии
- FastAPI + Jinja2 + HTMX
- Авторизация через классический логин/пароль (bcrypt)
- Hot-reload промптов из БД

---

## 9. Критические бизнес-правила

1. **chat_id** - основной идентификатор пользователя (НЕ telegram_user_id)
2. **Retry CRM** - максимум 2 попытки с интервалом 30 минут
3. **Контекст LLM** - максимум 20 последних сообщений
4. **Язык ответа** - ВСЕГДА на языке пользователя (автоматически)
5. **Каталог** - товары только в Chroma, услуги только в PostgreSQL
6. **Структура категорий** - обязательно три уровня (category_1, category_2, category_3)
7. **Поиск качество** - минимальный score 45%, boost по артикулу выше чем по названию
8. **Уведомления** - отдельно Email и Telegram с изоляцией каналов
9. **Индексация** - blue-green deployment без простоя
10. **AI расходы** - автоматическое отслеживание токенов с алертами админам при превышении лимитов

---

## 10. Переменные окружения

```env
# Основные
DATABASE_URL=postgresql://user:pass@postgres:5432/catalog_db
BOT_TOKEN=xxx
WEBHOOK_SECRET=xxx

# Режим работы контейнеров
DISABLE_TELEGRAM_BOT=false  # true для app контейнера, false для bot контейнера

# LLM (по умолчанию, меняется через админку)
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=xxx
YANDEX_API_KEY=xxx

# CRM
ZOHO_TOKEN_ENDPOINT=xxx

# Уведомления
SMTP_HOST=smtp.gmail.com
SMTP_USER=xxx
SMTP_PASSWORD=xxx
MANAGER_EMAILS=manager1@company.com,manager2@company.com
ADMIN_TELEGRAM_IDS=123456,789012
MANAGER_TELEGRAM_CHAT_ID=-100xxx

# Пути
CHROMA_PERSIST_DIR=/app/data/chroma
UPLOAD_DIR=/app/data/uploads

# Настройки поиска по каталогу
SEARCH_MIN_SCORE=0.45          # Минимальный score для показа результатов (0.0-1.0)
SEARCH_NAME_BOOST=0.2          # Boost за совпадения в названии товара (0.0-0.5)
SEARCH_ARTICLE_BOOST=0.3       # Boost за совпадения в артикуле (0.0-0.5)
SEARCH_MAX_RESULTS=10          # Максимальное количество результатов поиска

# AI модели и контроль расходов (NEW!)
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_AVAILABLE_MODELS=gpt-4o-mini,gpt-4o
YANDEX_DEFAULT_MODEL=yandexgpt-lite
YANDEX_AVAILABLE_MODELS=yandexgpt-lite,yandexgpt
MONTHLY_TOKEN_LIMIT=500000     # Месячный лимит токенов
MONTHLY_COST_LIMIT_USD=50.00   # Месячный лимит расходов
COST_ALERT_THRESHOLD=0.8       # Порог алерта (80%)
AUTO_DISABLE_ON_LIMIT=true     # Автоотключение при превышении
COST_ALERT_ENABLED=true        # Алерты включены
WEEKLY_USAGE_REPORT=true       # Еженедельные отчеты
```

---

## 11. Naming conventions

### Python
- Классы: `PascalCase` (UserService, LeadRepository)
- Функции/методы: `snake_case` (get_user, create_lead)
- Константы: `UPPER_SNAKE_CASE` (MAX_RETRIES)
- Приватные: `_leading_underscore`

### База данных
- Таблицы: `snake_case` множественное число (users, leads)
- Поля: `snake_case` (created_at, user_id)
- Индексы: `idx_table_fields` (idx_messages_conversation)

### API endpoints
- REST: `/api/v1/resource` (plural)
- Actions: POST `/api/v1/leads/qualify`

---

## 12. Интеграционные точки

### Внешние API
- Telegram Bot API (webhook + long polling fallback)
- Zoho CRM API v3:
  - Search API для проверки дубликатов (phone OR email)
  - Leads API для создания/обновления
  - Notes API для добавления заметок к существующим лидам
- LLM провайдеры (API keys)
- SMTP сервер

### Внутренние
- WebSocket для веб-виджета
- REST API для админки
- Health check endpoints
- Metrics endpoint (Prometheus format)

---

*Версия 2.0 - оптимизировано для Cursor AI*