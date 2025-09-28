"""
Роуты для управления услугами компании
"""
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.services.company_service_management import company_service_management
from ....domain.services.service_category_management import service_category_management
from ....domain.entities.admin_user import AdminUser
from ....infrastructure.database.connection import get_session
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from .admin import require_manager_or_admin

# Настройка шаблонов
templates = Jinja2Templates(directory="src/presentation/templates")

# Роутер для услуг
services_router = APIRouter(prefix="/admin/services", tags=["services"])


@services_router.get("/", response_class=HTMLResponse)
async def services_list(
    request: Request,
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    active_only: bool = Query(False),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница со списком всех услуг"""
    
    # Парсим категорию
    category_id = None
    if category:
        try:
            category_id = int(category)
        except ValueError:
            category_id = None
    
    # Получаем услуги
    services = await company_service_management.get_all_services(
        session, 
        active_only=active_only,
        search_term=search,
        category_id=category_id
    )
    
    # Статистика
    total_services = len(await company_service_management.get_all_services(session))
    active_services = len(await company_service_management.get_all_services(session, active_only=True))
    
    # Получаем категории из БД
    categories = await service_category_management.get_all_categories(session, active_only=True)
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Управление услугами",
        "services": services,
        "categories": categories,
        "total_services": total_services,
        "active_services": active_services,
        "search": search or "",
        "selected_category": category or "",
        "active_only": active_only,
        "message": request.session.pop("services_message", None),
        "error": request.session.pop("services_error", None),
    }
    return templates.TemplateResponse("admin/services_list.html", context)


@services_router.get("/create", response_class=HTMLResponse)
async def create_service_page(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница создания новой услуги"""
    # Получаем категории из БД
    categories = await service_category_management.get_all_categories(session, active_only=True)
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Создать новую услугу",
        "categories": categories,
        "error": request.session.pop("services_error", None),
        "message": request.session.pop("services_message", None),
    }
    return templates.TemplateResponse("admin/services_create.html", context)


@services_router.post("/create", response_class=RedirectResponse)
async def create_service_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    category_id: Optional[int] = Form(None),
    keywords: Optional[str] = Form(None),
    price_info: Optional[str] = Form(None),
    is_active: bool = Form(False),
    sort_order: int = Form(0),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Обработка создания новой услуги"""
    
    # Валидация
    if len(name.strip()) < 3:
        request.session["services_error"] = "Название должно содержать минимум 3 символа"
        return RedirectResponse(url="/admin/services/create", status_code=302)
    
    if len(description.strip()) < 10:
        request.session["services_error"] = "Описание должно содержать минимум 10 символов"
        return RedirectResponse(url="/admin/services/create", status_code=302)
    
    # Создаем услугу
    new_service = await company_service_management.create_service(
        session,
        name,
        description,
        current_user.id,
        category_id=category_id,
        keywords=keywords,
        price_info=price_info,
        is_active=is_active,
        sort_order=sort_order
    )
    
    if new_service:
        request.session["services_message"] = f"Услуга '{name}' успешно создана"
        return RedirectResponse(url=f"/admin/services/edit/{new_service.id}", status_code=302)
    else:
        request.session["services_error"] = "Ошибка при создании услуги"
        return RedirectResponse(url="/admin/services/create", status_code=302)


@services_router.get("/edit/{service_id}", response_class=HTMLResponse)
async def edit_service_page(
    request: Request,
    service_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница редактирования услуги"""
    service = await company_service_management.get_service_by_id(session, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": f"Редактировать услугу: {service.name}",
        "service": service,
        "categories": ServiceCategory,
        "error": request.session.pop("services_error", None),
        "message": request.session.pop("services_message", None),
    }
    return templates.TemplateResponse("admin/services_edit.html", context)


@services_router.post("/edit/{service_id}", response_class=RedirectResponse)
async def edit_service_post(
    request: Request,
    service_id: int,
    name: str = Form(...),
    description: str = Form(...),
    category: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    price_info: Optional[str] = Form(None),
    is_active: bool = Form(False),
    sort_order: int = Form(0),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Обработка редактирования услуги"""
    
    # Валидация
    if len(name.strip()) < 3:
        request.session["services_error"] = "Название должно содержать минимум 3 символа"
        return RedirectResponse(url=f"/admin/services/edit/{service_id}", status_code=302)
    
    if len(description.strip()) < 10:
        request.session["services_error"] = "Описание должно содержать минимум 10 символов"
        return RedirectResponse(url=f"/admin/services/edit/{service_id}", status_code=302)
    
    # Парсим категорию
    service_category = None
    if category:
        try:
            service_category = ServiceCategory(category)
        except ValueError:
            request.session["services_error"] = "Недопустимая категория"
            return RedirectResponse(url=f"/admin/services/edit/{service_id}", status_code=302)
    
    # Обновляем услугу
    success = await company_service_management.update_service(
        session,
        service_id,
        current_user.id,
        name=name,
        description=description,
        category=service_category,
        keywords=keywords,
        price_info=price_info,
        is_active=is_active,
        sort_order=sort_order
    )
    
    if success:
        request.session["services_message"] = f"Услуга '{name}' успешно обновлена"
    else:
        request.session["services_error"] = "Ошибка при обновлении услуги"
    
    return RedirectResponse(url=f"/admin/services/edit/{service_id}", status_code=302)


@services_router.post("/toggle/{service_id}", response_class=RedirectResponse)
async def toggle_service_status(
    request: Request,
    service_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Переключить статус активности услуги"""
    success = await company_service_management.toggle_service_status(
        session, service_id, current_user.id
    )
    
    if success:
        request.session["services_message"] = "Статус услуги изменен"
    else:
        request.session["services_error"] = "Ошибка при изменении статуса"
    
    return RedirectResponse(url="/admin/services/", status_code=302)


@services_router.post("/delete/{service_id}", response_class=RedirectResponse)
async def delete_service(
    request: Request,
    service_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Удалить услугу"""
    success = await company_service_management.delete_service(
        session, service_id, current_user.id
    )
    
    if success:
        request.session["services_message"] = "Услуга удалена"
    else:
        request.session["services_error"] = "Ошибка при удалении услуги"
    
    return RedirectResponse(url="/admin/services/", status_code=302)
