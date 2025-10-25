"""
API endpoints для управления настройками классификации запросов.
Позволяет администраторам гибко настраивать ключевые слова и логику классификации.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_session
from src.infrastructure.services.classification_settings_service import classification_settings_service
from src.application.web.routes.admin import get_current_admin_user, require_admin_user_with_redirect
from src.infrastructure.database.models import AdminUser
from src.presentation.template_config import templates


router = APIRouter(prefix="/admin", tags=["Classification Settings"])

logger = logging.getLogger(__name__)


@router.get("/classification-settings/api", response_class=HTMLResponse)
async def get_classification_settings_api(
    db: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    API endpoint для получения текущих настроек классификации.
    
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


@router.post("/classification-settings/settings")
async def update_classification_settings(
    settings_data: Dict[str, Any],
    db: AsyncSession = Depends(get_session),
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


@router.get("/classification-settings/settings/history")
async def get_classification_settings_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_session),
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


@router.post("/classification-settings/settings/reset")
async def reset_classification_settings(
    db: AsyncSession = Depends(get_session),
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


@router.post("/classification-settings/settings/clear-cache")
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


@router.post("/classification-settings/create", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def create_classification_settings(
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    enable_fast_classification: bool = Form(False),
    enable_llm_classification: bool = Form(False),
    product_keywords_str: str = Form(""),
    contact_keywords_str: str = Form(""),
    company_keywords_str: str = Form(""),
    availability_phrases_str: str = Form(""),
    search_words_str: str = Form(""),
    specific_products_str: str = Form(""),
    description: Optional[str] = Form(None)
):
    """Создает новые настройки классификации."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходима авторизация")
    
    if not current_user.can_edit_prompts():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    try:
        # Парсим строки в списки
        product_keywords = [k.strip() for k in product_keywords_str.split(',') if k.strip()]
        contact_keywords = [k.strip() for k in contact_keywords_str.split(',') if k.strip()]
        company_keywords = [k.strip() for k in company_keywords_str.split(',') if k.strip()]
        availability_phrases = [k.strip() for k in availability_phrases_str.split(',') if k.strip()]
        search_words = [k.strip() for k in search_words_str.split(',') if k.strip()]
        specific_products = [k.strip() for k in specific_products_str.split(',') if k.strip()]

        # Создаем новые настройки
        await classification_settings_service.create_settings(
            session=session,
            enable_fast_classification=enable_fast_classification,
            enable_llm_classification=enable_llm_classification,
            product_keywords=product_keywords,
            contact_keywords=contact_keywords,
            company_keywords=company_keywords,
            availability_phrases=availability_phrases,
            search_words=search_words,
            specific_products=specific_products,
            description=description,
            created_by_admin_id=current_user.id,
            is_active=False  # Новые настройки по умолчанию не активны
        )
        
        request.session["classification_success"] = "Новые настройки классификации созданы"
        
    except Exception as e:
        logger.error(f"Ошибка при создании настроек классификации: {e}")
        request.session["classification_error"] = f"Ошибка при создании настроек: {e}"
    
    return RedirectResponse(url="/admin/classification-settings", status_code=status.HTTP_302_FOUND)


@router.post("/classification-settings/initialize", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def initialize_classification_settings(
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Инициализирует дефолтные настройки классификации (только если их нет)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходима авторизация")
    
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


@router.post("/classification-settings/{settings_id}/activate", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def activate_classification_settings(
    settings_id: int,
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Активирует указанные настройки классификации."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходима авторизация")
    
    if not current_user.can_edit_prompts():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    try:
        success = await classification_settings_service.activate_settings(session, settings_id)
        if success:
            request.session["classification_success"] = f"Настройки классификации {settings_id} активированы"
        else:
            request.session["classification_error"] = f"Настройки классификации {settings_id} не найдены"
    except Exception as e:
        logger.error(f"Ошибка при активации настроек классификации {settings_id}: {e}")
        request.session["classification_error"] = f"Ошибка активации настроек: {e}"
    
    return RedirectResponse(url="/admin/classification-settings", status_code=status.HTTP_302_FOUND)


@router.get("/classification-settings/{settings_id}/edit", response_class=HTMLResponse)
async def edit_classification_settings_page(
    settings_id: int,
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Страница редактирования настроек классификации."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходима авторизация")
    
    if not current_user.can_edit_prompts():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    try:
        # Получаем настройки для редактирования
        from sqlalchemy import select
        from src.infrastructure.database.models import ClassificationSettings
        
        query = select(ClassificationSettings).where(ClassificationSettings.id == settings_id)
        result = await session.execute(query)
        settings = result.scalar_one_or_none()
        
        if not settings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Настройки не найдены")
        
        # Преобразуем настройки в словарь для шаблона
        settings_data = {
            "id": settings.id,
            "description": settings.description,
            "is_active": settings.is_active,
            "created_at": settings.created_at,
            "enable_fast_classification": settings.enable_fast_classification,
            "enable_llm_classification": settings.enable_llm_classification,
            "product_keywords": settings.product_keywords,
            "contact_keywords": settings.contact_keywords,
            "company_keywords": settings.company_keywords,
            "availability_phrases": settings.availability_phrases,
            "search_words": settings.search_words,
            "specific_products": settings.specific_products,
        }
        
        context = {
            "request": request,
            "current_user": current_user,
            "page_title": f"Редактирование настроек {settings_id}",
            "settings": settings_data
        }
        
        return templates.TemplateResponse("classification_settings_edit.html", context)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении настроек для редактирования {settings_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка загрузки настроек")


@router.post("/classification-settings/{settings_id}/update", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def update_classification_settings(
    settings_id: int,
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    enable_fast_classification: bool = Form(False),
    enable_llm_classification: bool = Form(False),
    product_keywords_str: str = Form(""),
    contact_keywords_str: str = Form(""),
    company_keywords_str: str = Form(""),
    availability_phrases_str: str = Form(""),
    search_words_str: str = Form(""),
    specific_products_str: str = Form(""),
    description: Optional[str] = Form(None)
):
    """Обновляет существующие настройки классификации."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходима авторизация")
    
    if not current_user.can_edit_prompts():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    try:
        # Парсим строки в списки
        product_keywords = [k.strip() for k in product_keywords_str.split(',') if k.strip()]
        contact_keywords = [k.strip() for k in contact_keywords_str.split(',') if k.strip()]
        company_keywords = [k.strip() for k in company_keywords_str.split(',') if k.strip()]
        availability_phrases = [k.strip() for k in availability_phrases_str.split(',') if k.strip()]
        search_words = [k.strip() for k in search_words_str.split(',') if k.strip()]
        specific_products = [k.strip() for k in specific_products_str.split(',') if k.strip()]

        # Обновляем настройки
        success = await classification_settings_service.update_existing_settings(
            session=session,
            settings_id=settings_id,
            enable_fast_classification=enable_fast_classification,
            enable_llm_classification=enable_llm_classification,
            product_keywords=product_keywords,
            contact_keywords=contact_keywords,
            company_keywords=company_keywords,
            availability_phrases=availability_phrases,
            search_words=search_words,
            specific_products=specific_products,
            description=description,
            updated_by_admin_id=current_user.id
        )
        
        if success:
            request.session["classification_success"] = f"Настройки классификации {settings_id} обновлены"
        else:
            request.session["classification_error"] = f"Настройки классификации {settings_id} не найдены"
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек классификации {settings_id}: {e}")
        request.session["classification_error"] = f"Ошибка обновления настроек: {e}"
    
    return RedirectResponse(url="/admin/classification-settings", status_code=status.HTTP_302_FOUND)
