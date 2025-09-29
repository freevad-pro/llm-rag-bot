"""
Роуты для управления общими настройками системы (только для администраторов)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ....infrastructure.database.connection import get_session
from .admin import require_admin_user
from ....infrastructure.database.models import AdminUser
from ....domain.services.settings_management import SettingsManagementService
from ....presentation.template_config import templates

router = APIRouter(prefix="/admin/settings", tags=["system-settings"])


@router.get("/", response_class=HTMLResponse)
async def system_settings_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Страница общих настроек системы (только для администраторов)
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    settings_service = SettingsManagementService()
    
    # Получаем все настройки
    all_settings = await settings_service.get_all_settings(session)
    
    # Определяем среду
    env_name, env_color = settings_service.get_environment()
    
    return templates.TemplateResponse(
        "admin/system_settings.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": "Общие настройки системы",
            "categories": settings_service.categories,
            "settings": all_settings,
            "environment": {
                "name": env_name,
                "color": env_color
            }
        }
    )


@router.post("/update-env")
async def update_env_setting(
    key: str = Form(...),
    value: str = Form(...),
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Обновление настройки в .env файле
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    settings_service = SettingsManagementService()
    
    # Валидируем настройку
    is_valid, error_message = settings_service.validate_setting(key, value, "text")
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": error_message}
        )
    
    # Обновляем настройку
    success = await settings_service.update_env_setting(key, value)
    
    if success:
        # Логируем изменение
        from ....infrastructure.logging.hybrid_logger import hybrid_logger
        await hybrid_logger.business(
            f"Администратор {current_user.username} изменил настройку {key}",
            metadata={
                "admin_id": current_user.id,
                "setting_key": key,
                "setting_value": value if not any(sensitive in key.lower() for sensitive in ['key', 'token', 'password', 'secret']) else "***",
                "requires_restart": True
            }
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Настройка обновлена. Требуется перезапуск приложения.",
                "requires_restart": True
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Ошибка при сохранении настройки"}
        )


@router.get("/test-connection/{service}")
async def test_connection(
    service: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Тестирование подключения к внешним сервисам
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    try:
        if service == "database":
            # Тестируем подключение к БД
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return JSONResponse(content={"success": True, "message": "Подключение к базе данных работает"})
        
        elif service == "openai":
            # Тестируем OpenAI API
            from ....infrastructure.llm.providers.openai_provider import OpenAIProvider
            from ....config.settings import Settings
            settings = Settings()
            
            if not settings.openai_api_key:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "OpenAI API ключ не настроен"}
                )
            
            try:
                # Создаем провайдер с правильной конфигурацией (словарь)
                provider_config = {
                    "api_key": settings.openai_api_key,
                    "model": settings.openai_default_model,
                    "timeout": 30
                }
                provider = OpenAIProvider(provider_config)
                
                # Используем существующий метод is_healthy()
                is_healthy = await provider.is_healthy()
                if is_healthy:
                    return JSONResponse(content={
                        "success": True, 
                        "message": f"OpenAI API работает. Модель: {settings.openai_default_model}"
                    })
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "error": "OpenAI API недоступен или неверный ключ"}
                    )
            except Exception as e:
                # Логируем ошибку проверки
                from ....infrastructure.logging.hybrid_logger import hybrid_logger
                await hybrid_logger.error(f"Ошибка проверки OpenAI провайдера: {e}")
                
                return JSONResponse(
                    status_code=500,
                    content={"success": False, "error": f"Ошибка инициализации провайдера: {str(e)}"}
                )
        
        elif service == "telegram":
            # Тестируем Telegram Bot API
            import aiohttp
            from ....config.settings import Settings
            settings = Settings()
            
            if not settings.bot_token:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Telegram Bot Token не настроен"}
                )
            
            async with aiohttp.ClientSession() as client:
                url = f"https://api.telegram.org/bot{settings.bot_token}/getMe"
                async with client.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        bot_info = data.get("result", {})
                        return JSONResponse(content={
                            "success": True,
                            "message": f"Telegram Bot API работает. Бот: @{bot_info.get('username', 'unknown')}"
                        })
                    else:
                        return JSONResponse(
                            status_code=400,
                            content={"success": False, "error": "Неверный Telegram Bot Token"}
                        )
        
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Неизвестный сервис: {service}"}
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Ошибка тестирования: {str(e)}"}
        )


@router.get("/export")
async def export_settings(
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Экспорт настроек в JSON (без чувствительных данных)
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    settings_service = SettingsManagementService()
    all_settings = await settings_service.get_all_settings(session)
    
    # Подготавливаем данные для экспорта (без чувствительных)
    export_data = {}
    for category_name, settings_list in all_settings.items():
        export_data[category_name] = {}
        for setting in settings_list:
            if not setting.is_sensitive:
                export_data[category_name][setting.key] = {
                    "value": setting.value,
                    "title": setting.title,
                    "description": setting.description,
                    "type": setting.setting_type,
                    "source": setting.source
                }
    
    # Логируем экспорт
    from ....infrastructure.logging.hybrid_logger import hybrid_logger
    await hybrid_logger.business(
        f"Администратор {current_user.username} экспортировал настройки системы",
        metadata={
            "admin_id": current_user.id,
            "categories_count": len(export_data),
            "settings_count": sum(len(settings) for settings in export_data.values())
        }
    )
    
    return JSONResponse(content=export_data)


@router.post("/restart-application")
async def restart_application(
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Перезапуск приложения (только в Docker окружении)
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    try:
        # Логируем перезапуск
        from ....infrastructure.logging.hybrid_logger import hybrid_logger
        await hybrid_logger.business(
            f"Администратор {current_user.username} запросил перезапуск приложения",
            metadata={"admin_id": current_user.id}
        )
        
        # В Docker окружении перезапуск должен выполняться извне
        # Возвращаем инструкции для ручного перезапуска
        return JSONResponse(content={
            "success": True,
            "message": "Для применения изменений выполните команду: docker-compose restart app",
            "manual_restart": True
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Ошибка перезапуска: {str(e)}"}
        )
