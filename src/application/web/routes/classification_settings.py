"""
API endpoints для управления настройками классификации запросов.
Позволяет администраторам гибко настраивать ключевые слова и логику классификации.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.database.connection import get_db
from ...infrastructure.services.classification_settings_service import classification_settings_service
from ...application.web.dependencies import get_current_admin_user
from ...infrastructure.database.models import AdminUser


router = APIRouter(prefix="/api/v1/classification", tags=["Classification Settings"])


@router.get("/settings")
async def get_classification_settings(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Получает текущие настройки классификации.
    
    Returns:
        Словарь с настройками классификации
    """
    try:
        settings = await classification_settings_service.get_active_settings(db)
        return {
            "success": True,
            "data": settings
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения настроек: {str(e)}"
        )


@router.post("/settings")
async def update_classification_settings(
    settings_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Обновляет настройки классификации.
    
    Args:
        settings_data: Новые настройки классификации
        
    Returns:
        Результат обновления
    """
    try:
        # Валидация данных
        required_fields = [
            "enable_fast_classification",
            "enable_llm_classification"
        ]
        
        for field in required_fields:
            if field not in settings_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Отсутствует обязательное поле: {field}"
                )
        
        # Обновляем настройки
        success = await classification_settings_service.update_settings(
            db, current_user.id, settings_data
        )
        
        if success:
            return {
                "success": True,
                "message": "Настройки классификации успешно обновлены"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка обновления настроек"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления настроек: {str(e)}"
        )


@router.get("/settings/history")
async def get_classification_settings_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Получает историю изменений настроек классификации.
    
    Args:
        limit: Максимальное количество записей
        
    Returns:
        Список настроек с метаданными
    """
    try:
        history = await classification_settings_service.get_settings_history(db, limit)
        return {
            "success": True,
            "data": history
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения истории: {str(e)}"
        )


@router.post("/settings/reset")
async def reset_classification_settings(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Сбрасывает настройки классификации к значениям по умолчанию.
    
    Returns:
        Результат сброса
    """
    try:
        # Получаем настройки по умолчанию
        default_settings = classification_settings_service._get_default_settings()
        
        # Обновляем настройки
        success = await classification_settings_service.update_settings(
            db, current_user.id, default_settings
        )
        
        if success:
            return {
                "success": True,
                "message": "Настройки классификации сброшены к значениям по умолчанию"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка сброса настроек"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сброса настроек: {str(e)}"
        )


@router.post("/settings/clear-cache")
async def clear_classification_cache(
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Очищает кеш настроек классификации для принудительного обновления.
    
    Returns:
        Результат очистки кеша
    """
    try:
        classification_settings_service.clear_cache()
        return {
            "success": True,
            "message": "Кеш настроек классификации очищен"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки кеша: {str(e)}"
        )


@router.post("/classification-settings/initialize", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def initialize_classification_settings(
    request: Request,
    current_user: AdminUser = Depends(require_admin_user_with_redirect),
    session: AsyncSession = Depends(get_session)
):
    """Инициализирует дефолтные настройки классификации (только если их нет)."""
    if not current_user.can_edit_prompts():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    try:
        result = await classification_settings_service.initialize_default_settings(session, current_user.id)
        if result:
            request.session["classification_success"] = "Дефолтные настройки классификации инициализированы"
        else:
            request.session["classification_info"] = "Настройки классификации уже существуют"
    except Exception as e:
        logger.error(f"Ошибка при инициализации настроек классификации: {e}")
        request.session["classification_error"] = "Ошибка инициализации настроек классификации"
    
    return RedirectResponse(url="/admin/classification-settings", status_code=status.HTTP_302_FOUND)
