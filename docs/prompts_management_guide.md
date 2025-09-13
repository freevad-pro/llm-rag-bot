# 📝 Руководство по управлению промптами ИИ-бота

## 🎯 Обзор системы промптов

### Что такое промпты в нашей системе?
Промпты - это специализированные инструкции для ИИ, которые определяют:
- Как бот отвечает на разные типы запросов
- Какую информацию о компании KeTai Consulting он использует
- Как он квалифицирует лидов и обрабатывает возражения

### Типы промптов в системе:

#### 🏠 **Базовые промпты:**
1. `system_prompt` - основная личность бота
2. `product_search_prompt` - поиск по каталогу товаров
3. `service_answer_prompt` - ответы об услугах компании
4. `general_conversation_prompt` - общие диалоги
5. `lead_qualification_prompt` - квалификация потенциальных клиентов
6. `company_info_prompt` - информация о компании

#### ⚡ **Специализированные промпты:**
7. `welcome_prompt` - приветствие новых пользователей
8. `pricing_inquiry_prompt` - работа с запросами о ценах
9. `technical_clarification_prompt` - сбор технических требований
10. `objection_handling_prompt` - обработка возражений клиентов
11. `error_handling_prompt` - обработка ошибок
12. `conversation_closing_prompt` - завершение диалогов

---

## 🛠️ Способы обновления промптов

### 1️⃣ **Автоматическое обновление (рекомендуется)**

Используйте готовые скрипты для массового обновления:

```bash
# Генерируем SQL скрипт с новыми промптами
python scripts/quick_update_prompts.py

# Копируем скрипт в контейнер PostgreSQL
docker cp temp/update_prompts.sql llm-rag-bot-postgres-1:/tmp/

# Выполняем обновление
docker-compose exec postgres psql -U postgres -d catalog_db -f /tmp/update_prompts.sql

# Перезапускаем приложение
docker-compose restart app
```

### 2️⃣ **Обновление конкретного промпта**

Для изменения одного промпта через SQL:

```sql
-- Деактивируем старую версию
UPDATE prompts SET active = false WHERE name = 'system_prompt';

-- Добавляем новую версию
INSERT INTO prompts (name, content, version, active, created_at, updated_at) VALUES (
    'system_prompt',
    'Ваш новый текст промпта здесь...',
    2,  -- увеличиваем версию
    true,
    NOW(),
    NOW()
);
```

### 3️⃣ **Через админку (будущая возможность)**

После реализации веб-интерфейса:
- Откройте http://localhost:8000/admin
- Перейдите в раздел "Управление промптами"
- Редактируйте промпты через веб-форму

---

## 📋 Пошаговые инструкции

### 🚀 **Быстрое обновление всех промптов**

1. **Убедитесь что контейнеры запущены:**
   ```bash
   docker-compose ps
   ```

2. **Сгенерируйте SQL скрипт:**
   ```bash
   python scripts/quick_update_prompts.py
   ```

3. **Примените обновления:**
   ```bash
   docker cp temp/update_prompts.sql llm-rag-bot-postgres-1:/tmp/
   docker-compose exec postgres psql -U postgres -d catalog_db -f /tmp/update_prompts.sql
   ```

4. **Перезапустите бота:**
   ```bash
   docker-compose restart app
   ```

5. **Проверьте что все работает:**
   ```bash
   curl http://localhost:8000/health
   ```

### 🔧 **Создание нового промпта**

1. **Добавьте промпт в файл `src/infrastructure/llm/services/improved_prompts.py`:**
   ```python
   IMPROVED_PROMPTS = {
       # ... существующие промпты ...
       "new_prompt_name": """
       Ваш новый промпт здесь...
       """
   }
   ```

2. **Выполните обновление по инструкции выше**

### 📊 **Проверка текущих промптов**

```bash
# Количество промптов
docker-compose exec postgres psql -U postgres -d catalog_db -c "SELECT COUNT(*) FROM prompts WHERE active = true;"

# Список активных промптов
docker-compose exec postgres psql -U postgres -d catalog_db -c "SELECT name, version FROM prompts WHERE active = true ORDER BY name;"

# Содержимое конкретного промпта
docker-compose exec postgres psql -U postgres -d catalog_db -c "SELECT content FROM prompts WHERE name = 'system_prompt' AND active = true;"
```

---

## ⚠️ Важные моменты

### 🔒 **Безопасность:**
- Всегда делайте backup перед массовым обновлением
- Тестируйте новые промпты на development среде
- Сохраняйте старые версии через версионирование

### 📝 **Правила написания промптов:**

#### ✅ **Хорошие практики:**
- Упоминайте название компании "KeTai Consulting"
- Указывайте минимальные суммы сотрудничества
- Подчеркивайте уникальные преимущества
- Используйте эмодзи для структурирования
- Заканчивайте призывом к действию

#### ❌ **Чего избегать:**
- Слишком общих формулировок
- Обещаний которые компания не может выполнить
- Технических терминов без объяснений
- Слишком длинных промптов (>500 слов)

### 🎯 **Специфика для KeTai Consulting:**

Все промпты должны отражать:
- **Фокус на Китай:** поставки, производство, логистика
- **Финансовые пороги:** от 100,000 ₽ для поставок, от 150,000 ₽ для производства
- **Принципы:** честность, доверие, прозрачность
- **Услуги "под ключ":** полный цикл от идеи до доставки
- **Экспертизу:** знание китайского рынка и культуры

---

## 🔄 Workflow обновления

### Development → Production:

1. **Разработка промптов локально**
2. **Тестирование на dev контейнерах**
3. **Коммит изменений в Git**
4. **Деплой на production сервер**
5. **Применение промптов на production**
6. **Мониторинг качества ответов**

### Версионирование:

- Каждое изменение промпта = новая версия
- Старые версии остаются в БД (active = false)
- Возможность отката к предыдущей версии
- Changelog в Git коммитах

---

## 📱 Полезные команды

### Backup промптов:
```bash
# Экспорт всех промптов
docker-compose exec postgres pg_dump -U postgres -d catalog_db -t prompts > backup_prompts.sql

# Восстановление
docker-compose exec postgres psql -U postgres -d catalog_db < backup_prompts.sql
```

### Мониторинг:
```bash
# Логи изменений промптов
docker-compose logs app | grep -i prompt

# Проверка использования кэша
curl http://localhost:8000/admin/prompts/cache/status
```

### Отладка:
```bash
# Тест конкретного промпта
python scripts/test_prompt.py system_prompt "Привет, что вы делаете?"

# Сравнение версий промптов
python scripts/update_prompts.py diff system_prompt
```

---

## 🎯 Заключение

Система управления промптами позволяет:
- ✅ Быстро адаптировать поведение бота
- ✅ A/B тестировать разные подходы
- ✅ Версионировать и откатывать изменения  
- ✅ Специализировать ответы под KeTai Consulting
- ✅ Масштабировать систему для новых услуг

**💡 Совет:** Регулярно анализируйте диалоги с клиентами и корректируйте промпты для улучшения конверсии!

---

## 🚀 Быстрая справка-шпаргалка

### ⚡ Команды для быстрого обновления:

```bash
# 1. Генерируем SQL скрипт
python scripts/quick_update_prompts.py

# 2. Применяем изменения
docker cp temp/update_prompts.sql llm-rag-bot-postgres-1:/tmp/
docker-compose exec postgres psql -U postgres -d catalog_db -f /tmp/update_prompts.sql

# 3. Перезапускаем бота
docker-compose restart app
```

### 📋 Команды для проверки:

```bash
# Количество активных промптов (должно быть 12)
docker-compose exec postgres psql -U postgres -d catalog_db -c "SELECT COUNT(*) FROM prompts WHERE active = true;"

# Список всех промптов
docker-compose exec postgres psql -U postgres -d catalog_db -c "SELECT name, version FROM prompts WHERE active = true ORDER BY name;"
```

### 📁 Ключевые файлы:

- **Исходные промпты:** `src/infrastructure/llm/services/improved_prompts.py`
- **Генератор SQL:** `scripts/quick_update_prompts.py`
- **Анализ (архив):** `docs/archive_prompts_analysis_sept2025.md`

### ❗ Важные принципы:

- ✅ Все промпты адаптированы под **KeTai Consulting**
- ✅ Указывают минимальные суммы: **100,000 ₽** (поставки), **150,000 ₽** (производство)
- ✅ Подчеркивают **экспертизу в работе с Китаем**
- ✅ Направлены на **конверсию и квалификацию лидов**
