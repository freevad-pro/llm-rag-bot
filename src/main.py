"""
Главный файл приложения FastAPI
Health check endpoint и базовая структура
"""
import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import bcrypt
from sqlalchemy import select

# Отключаем телеметрию aiogram (исправляет ошибку capture())
os.environ["AIOGRAM_DISABLE_TELEMETRY"] = "1"

from src.config.settings import settings
from src.infrastructure.database.connection import create_tables, get_db_health, get_session
from src.infrastructure.database.models import AdminUser
from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.application.telegram.bot import start_bot, stop_bot
from src.application.web.routes.admin import admin_router
from src.application.web.routes.prompts import prompts_router
from src.application.web.routes.services import services_router
from src.application.web.routes.categories import categories_router
from src.application.web.routes.classification_settings import router as classification_settings_router
from src.application.web.routes.logs import logs_router
from src.application.web.routes.users import router as users_router
from src.application.web.routes.catalog import catalog_router
from src.application.web.routes.model_management import model_router
from src.application.web.routes.company_info import router as company_info_router
from src.application.web.routes.database import router as database_router
from src.application.web.routes.system_settings import router as system_settings_router
from src.application.web.routes.usage_statistics import router as usage_statistics_router
from src.application.web.routes.leads import router as leads_router
from src.domain.services.prompt_management import PromptManagementService


async def create_default_admin():
    """
    Создает администратора по умолчанию при первом запуске приложения.
    Выполняется только если в системе нет ни одного администратора.
    """
    try:
        async for session in get_session():
            # Проверяем, есть ли уже администраторы
            result = await session.execute(select(AdminUser))
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                await hybrid_logger.info(f"Администратор уже существует: {existing_admin.username}")
                return
            
            # Создаем администратора по умолчанию
            username = "admin"
            password = "admin123"
            email = "admin@example.com"
            
            # Хешируем пароль
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            admin_user = AdminUser(
                username=username,
                email=email,
                password_hash=password_hash,
                role="ADMIN",
                is_active=True,
                first_name="Администратор",
                last_name="Системы"
            )
            
            session.add(admin_user)
            await session.commit()
            
            await hybrid_logger.info(f"Создан администратор по умолчанию: {username}")
            await hybrid_logger.warning("⚠️  ВАЖНО: Смените пароль администратора после первого входа!")
            return
            
    except Exception as e:
        await hybrid_logger.error(f"Ошибка создания администратора по умолчанию: {e}")


async def initialize_default_prompts():
    """
    Инициализирует промпты по умолчанию при первом запуске приложения.
    Выполняется только если в системе нет промптов.
    """
    try:
        prompt_service = PromptManagementService()
        async for session in get_session():
            await prompt_service.initialize_default_prompts(session)
            await hybrid_logger.info("Промпты по умолчанию инициализированы")
            return
            
    except Exception as e:
        await hybrid_logger.error(f"Ошибка инициализации промптов по умолчанию: {e}")


class TelegramCSPMiddleware(BaseHTTPMiddleware):
    """Middleware для настройки CSP headers для работы с Telegram Login Widget"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Для админ-панели полностью отключаем CSP ограничения
        if request.url.path.startswith("/admin"):
            # Удаляем все ограничительные headers
            headers_to_remove = [
                "content-security-policy", 
                "x-frame-options", 
                "x-content-type-options",
                "referrer-policy"
            ]
            
            for header in headers_to_remove:
                if header in response.headers:
                    del response.headers[header]
            
        return response


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
        
        # Создание администратора по умолчанию (если не существует)
        await create_default_admin()
        
        # Инициализация промптов по умолчанию (если их нет)
        await initialize_default_prompts()
        
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

# Exception handler для обработки редиректов при неавторизованном доступе
@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    """
    Обрабатывает исключения авторизации и делает редирект для HTML запросов
    """
    # Проверяем, это ли запрос на авторизацию и HTML ли это
    if (exc.status_code == 401 and 
        request.url.path.startswith("/admin") and 
        not request.url.path.startswith("/admin/login") and
        request.headers.get("accept", "").startswith("text/html")):
        
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Для всех остальных случаев возвращаем стандартный JSON ответ
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Middleware
app.add_middleware(TelegramCSPMiddleware)

app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.secret_key or "change-me-in-production"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="src/presentation/static"), name="static")

# Подключение роутеров
app.include_router(admin_router)
app.include_router(prompts_router)
app.include_router(services_router)
app.include_router(categories_router)
app.include_router(classification_settings_router)
app.include_router(logs_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(model_router)
app.include_router(company_info_router)
app.include_router(database_router)
app.include_router(system_settings_router)
app.include_router(usage_statistics_router)
app.include_router(leads_router)


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
        "health": "/health",
        "admin": "/admin/"
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
