"""
Утилиты для работы с Telegram Bot.
Согласно @conventions.md - правильное управление ресурсами.
"""
from contextlib import asynccontextmanager
from aiogram import Bot
from src.config.settings import settings


@asynccontextmanager
async def get_bot_for_notifications():
    """
    Контекстный менеджер для создания Bot для отправки уведомлений.
    Гарантирует закрытие сессии после использования для предотвращения утечки ресурсов.
    
    Usage:
        async with get_bot_for_notifications() as bot:
            notifier = get_telegram_notifier(bot)
            await notifier.notify_new_lead(lead, chat_id)
    
    Yields:
        Bot: Экземпляр aiogram Bot
        
    Raises:
        ValueError: Если BOT_TOKEN не настроен
    """
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN не установлен в настройках")
    
    bot = Bot(token=settings.bot_token)
    try:
        yield bot
    finally:
        await bot.session.close()

