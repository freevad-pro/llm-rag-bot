"""
Основной файл Telegram бота на aiogram 3.x
Согласно @vision.md - полностью асинхронный
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config.settings import settings
from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.application.telegram.handlers import basic_handlers
from src.application.telegram.handlers.search_handlers import SearchHandlers
from src.application.telegram.handlers.llm_handlers import create_llm_handlers
from src.application.telegram.handlers.lead_handlers import LeadHandlers
from src.application.telegram.middleware import DatabaseMiddleware
from src.application.telegram.services import message_service
from src.application.telegram.services.lead_service import LeadService
from src.infrastructure.search.catalog_service import CatalogSearchService
from src.infrastructure.notifications.telegram_notifier import get_telegram_notifier
from src.infrastructure.tasks.inactive_users_monitor import get_inactive_users_monitor


async def create_bot() -> Bot:
    """Создание экземпляра бота"""
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN не установлен в переменных окружения")
    
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    await hybrid_logger.info("Telegram бот создан")
    return bot


async def create_dispatcher(bot: Bot) -> Dispatcher:
    """Создание и настройка диспетчера"""
    dp = Dispatcher()
    
    # Подключаем middleware для работы с БД
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Инициализируем сервисы
    catalog_service = CatalogSearchService()
    lead_service = LeadService()
    
    # Создаем обработчики
    search_handlers = SearchHandlers(catalog_service)
    llm_handlers = create_llm_handlers()
    lead_handlers = LeadHandlers(lead_service)
    
    # Подключаем обработчики (порядок важен!)
    dp.include_router(lead_handlers.router)      # Первый - самые специфичные
    dp.include_router(search_handlers.router)    # Поисковые callback'и
    dp.include_router(basic_handlers.router)     # Основные команды (приоритет ниже)
    dp.include_router(llm_handlers.router)       # Последний - обрабатывает весь текст
    
    # Инициализируем уведомления и мониторинг
    notifier = get_telegram_notifier(bot)
    monitor = get_inactive_users_monitor(lead_service, notifier)
    
    # Запускаем мониторинг неактивных пользователей
    await monitor.start()
    
    await hybrid_logger.info("Dispatcher настроен с поддержкой поиска, LLM и управления лидами")
    return dp


async def start_bot():
    """Запуск бота"""
    try:
        await hybrid_logger.info("Запуск Telegram бота...")
        
        bot = await create_bot()
        dp = await create_dispatcher(bot)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        await hybrid_logger.info(f"Бот запущен: @{bot_info.username}")
        
        # Запуск polling
        await dp.start_polling(bot)
        
    except Exception as e:
        await hybrid_logger.critical(f"Критическая ошибка запуска бота: {e}")
        raise
    finally:
        await hybrid_logger.info("Telegram бот остановлен")


async def stop_bot(bot: Bot):
    """Остановка бота"""
    await bot.session.close()
    await hybrid_logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    # Для локального запуска
    asyncio.run(start_bot())
