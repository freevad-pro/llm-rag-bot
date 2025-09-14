"""
Главный файл приложения FastAPI
Health check endpoint и базовая структура
"""
import os
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio

# Отключаем телеметрию aiogram (исправляет ошибку capture())
os.environ["AIOGRAM_DISABLE_TELEMETRY"] = "1"

from src.config.settings import settings
from src.infrastructure.database.connection import create_tables, get_db_health
from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.application.telegram.bot import start_bot, stop_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle события приложения"""
    # Startup
    await hybrid_logger.info("Запуск приложения LLM RAG Bot...")
    
    bot_task = None
    try:
        # Инициализация БД
        await create_tables()
        await hybrid_logger.info("База данных инициализирована")
        
        # Запуск Telegram бота если токен настроен И бот не отключен
        if settings.bot_token and not settings.disable_telegram_bot:
            bot_task = asyncio.create_task(start_bot())
            await hybrid_logger.info("Telegram бот запущен в фоновом режиме")
        elif settings.disable_telegram_bot:
            await hybrid_logger.info("Telegram бот отключен через DISABLE_TELEGRAM_BOT")
        else:
            await hybrid_logger.warning("BOT_TOKEN не настроен, Telegram бот не запущен")
        
        yield
        
    except Exception as e:
        await hybrid_logger.critical(f"Ошибка запуска приложения: {e}")
        raise
    finally:
        # Shutdown
        if bot_task:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
            await hybrid_logger.info("Telegram бот остановлен")
        
        await hybrid_logger.info("Завершение работы приложения")


# Создание FastAPI приложения
app = FastAPI(
    title="LLM RAG Bot",
    description="AI Agent for client consultation with 40K+ product catalog",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint для мониторинга
    Проверяет состояние основных компонентов системы
    """
    try:
        # Проверка БД
        db_status = await get_db_health()
        
        # Базовая информация о системе
        health_data = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0",
            "environment": "development" if settings.debug else "production",
            "components": {
                **db_status,
                # TODO: В следующих итерациях добавить проверку других компонентов
                # "telegram": "not_implemented",
                # "chroma": "not_implemented", 
                # "llm": "not_implemented"
            }
        }
        
        # Определяем общий статус
        if db_status.get("database") != "connected":
            health_data["status"] = "degraded"
            return JSONResponse(
                status_code=503,
                content=health_data
            )
        
        return JSONResponse(content=health_data)
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "LLM RAG Bot API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/api/info")
async def api_info():
    """Информация об API"""
    return {
        "name": "LLM RAG Bot",
        "version": "0.1.0",
        "iteration": "MVP-2",
        "features": {
            "telegram_bot": "implemented" if settings.bot_token else "not_configured",
            "catalog_search": "not_implemented", 
            "lead_management": "not_implemented",
            "admin_panel": "not_implemented"
        },
        "database": "connected",
        "telegram_configured": bool(settings.bot_token),
        "debug": settings.debug
    }


async def run_bot_only():
    """Запуск только Telegram бота без FastAPI"""
    await hybrid_logger.info("Запуск Telegram бота...")
    
    try:
        # Инициализация БД
        await create_tables()
        await hybrid_logger.info("База данных инициализирована")
        
        # Проверка токена
        if not settings.bot_token:
            await hybrid_logger.critical("BOT_TOKEN не настроен!")
            return
        
        # Запуск бота
        await start_bot()
        
    except Exception as e:
        await hybrid_logger.critical(f"Ошибка запуска бота: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == "bot":
        # Запуск только бота
        asyncio.run(run_bot_only())
    else:
        # Запуск FastAPI сервера
        import uvicorn
        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
