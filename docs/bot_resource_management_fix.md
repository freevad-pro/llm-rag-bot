# Исправление утечки ресурсов Bot

**Дата:** 18 октября 2025  
**Проблема:** Утечка ресурсов при создании экземпляров `Bot` без закрытия сессии

---

## 🐛 Обнаруженные проблемы

### 1. `lead_handlers.py` (строка 819)
```python
# ❌ ДО: Создавался Bot без закрытия сессии
bot = Bot(token=settings.bot_token)
notifier = get_telegram_notifier(bot)
success = await notifier.notify_new_lead(lead, chat_id)
# Сессия bot никогда не закрывалась → утечка ресурсов
```

### 2. `cost_alert_service.py` (строка 184)
```python
# ❌ ДО: Bot создавался один раз и хранился в _bot
async def _get_bot(self):
    if self._bot is None:
        self._bot = Bot(token=self.settings.bot_token)
    return self._bot
# Сессия никогда не закрывалась → утечка ресурсов
```

---

## ✅ Решение: Контекстный менеджер

### Создан модуль: `src/infrastructure/utils/bot_utils.py`

```python
from contextlib import asynccontextmanager
from aiogram import Bot
from src.config.settings import settings

@asynccontextmanager
async def get_bot_for_notifications():
    """
    Контекстный менеджер для создания Bot для отправки уведомлений.
    Гарантирует закрытие сессии после использования.
    """
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN не установлен в настройках")
    
    bot = Bot(token=settings.bot_token)
    try:
        yield bot
    finally:
        await bot.session.close()  # ✅ Всегда закрывается
```

---

## 📝 Применённые исправления

### 1. `lead_handlers.py`

```python
# ✅ ПОСЛЕ: Используем контекстный менеджер
from src.infrastructure.utils.bot_utils import get_bot_for_notifications

async with get_bot_for_notifications() as bot:
    notifier = get_telegram_notifier(bot)
    success = await notifier.notify_new_lead(lead, chat_id)
# Сессия автоматически закрывается при выходе из блока with
```

### 2. `cost_alert_service.py`

```python
# ✅ ПОСЛЕ: Используем контекстный менеджер
from src.infrastructure.utils.bot_utils import get_bot_for_notifications

async with get_bot_for_notifications() as bot:
    for admin_id in admin_ids:
        await bot.send_message(chat_id=admin_id, text=message)
# Сессия автоматически закрывается после отправки всех сообщений

# Удалено:
# - self._bot = None из __init__
# - метод _get_bot() полностью
```

---

## 🎯 Преимущества решения

1. **Гарантированное закрытие ресурсов** - даже при исключениях
2. **Переиспользуемость** - один паттерн для всех мест
3. **Соответствие Python best practices** - context managers
4. **Читаемость** - явно видна область жизни объекта
5. **Соответствие Clean Architecture** - правильное управление инфраструктурными ресурсами

---

## 🔍 Проверка

Все места создания `Bot` теперь используют контекстный менеджер:
- ✅ `lead_handlers.py` - метод `_notify_managers()`
- ✅ `cost_alert_service.py` - метод `_send_to_admins()`
- ℹ️ `bot.py` - основной бот управляется через `lifespan` в `main.py`

---

## 📚 Ссылки

- Принцип из `@conventions.md` - правильное управление ресурсами
- Требование из `@README.md` - 99.5% доступности (утечки ресурсов снижают стабильность)
- Python Context Managers: https://docs.python.org/3/library/contextlib.html

---

*Исправление предотвращает утечку HTTP сессий aiogram Bot, что улучшает стабильность и производительность системы.*

