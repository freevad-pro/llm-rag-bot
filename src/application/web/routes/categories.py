"""
Роуты для управления категориями услуг
"""
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.services.service_category_management import service_category_management
from ....domain.entities.admin_user import AdminUser
from ....infrastructure.database.connection import get_session
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from .admin import require_manager_or_admin

# Настройка шаблонов
templates = Jinja2Templates(directory="src/presentation/templates")

# Роутер для категорий
categories_router = APIRouter(prefix="/admin/categories", tags=["categories"])


@categories_router.get("/", response_class=HTMLResponse)
async def categories_list(
    request: Request,
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница со списком всех категорий"""
    
    # Получаем категории
    categories = await service_category_management.get_all_categories(
        session, 
        active_only=active_only,
        search_term=search
    )
    
    # Статистика
    total_categories = len(await service_category_management.get_all_categories(session))
    active_categories = len(await service_category_management.get_all_categories(session, active_only=True))
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Управление категориями услуг",
        "categories": categories,
        "total_categories": total_categories,
        "active_categories": active_categories,
        "search": search or "",
        "active_only": active_only,
        "message": request.session.pop("categories_message", None),
        "error": request.session.pop("categories_error", None),
    }
    return templates.TemplateResponse("admin/categories_list.html", context)


@categories_router.get("/create", response_class=HTMLResponse)
async def create_category_page(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin)
):
    """Страница создания новой категории"""
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Создать новую категорию",
        "error": request.session.pop("categories_error", None),
        "message": request.session.pop("categories_message", None),
    }
    return templates.TemplateResponse("admin/categories_create.html", context)


@categories_router.post("/create", response_class=RedirectResponse)
async def create_category_post(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    icon: Optional[str] = Form(None),
    is_active: bool = Form(False),
    sort_order: int = Form(0),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Обработка создания новой категории"""
    
    # Валидация
    if len(name.strip()) < 2:
        request.session["categories_error"] = "Техническое имя должно содержать минимум 2 символа"
        return RedirectResponse(url="/admin/categories/create", status_code=302)
    
    if len(display_name.strip()) < 2:
        request.session["categories_error"] = "Название должно содержать минимум 2 символа"
        return RedirectResponse(url="/admin/categories/create", status_code=302)
    
    # Проверяем формат цвета
    if color and not color.startswith('#'):
        color = f"#{color.lstrip('#')}"
    
    if color and len(color) != 7:
        request.session["categories_error"] = "Цвет должен быть в формате #RRGGBB"
        return RedirectResponse(url="/admin/categories/create", status_code=302)
    
    # Создаем категорию
    new_category = await service_category_management.create_category(
        session,
        name,
        display_name,
        current_user.id,
        description=description,
        color=color,
        icon=icon,
        is_active=is_active,
        sort_order=sort_order
    )
    
    if new_category:
        request.session["categories_message"] = f"Категория '{display_name}' успешно создана"
        return RedirectResponse(url=f"/admin/categories/edit/{new_category.id}", status_code=302)
    else:
        request.session["categories_error"] = "Ошибка при создании категории (возможно, имя уже существует)"
        return RedirectResponse(url="/admin/categories/create", status_code=302)


@categories_router.get("/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_page(
    request: Request,
    category_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница редактирования категории"""
    category = await service_category_management.get_category_by_id(session, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": f"Редактировать категорию: {category.display_name}",
        "category": category,
        "error": request.session.pop("categories_error", None),
        "message": request.session.pop("categories_message", None),
    }
    return templates.TemplateResponse("admin/categories_edit.html", context)


@categories_router.post("/edit/{category_id}", response_class=RedirectResponse)
async def edit_category_post(
    request: Request,
    category_id: int,
    name: str = Form(...),
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    icon: Optional[str] = Form(None),
    is_active: bool = Form(False),
    sort_order: int = Form(0),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Обработка редактирования категории"""
    
    # Валидация
    if len(name.strip()) < 2:
        request.session["categories_error"] = "Техническое имя должно содержать минимум 2 символа"
        return RedirectResponse(url=f"/admin/categories/edit/{category_id}", status_code=302)
    
    if len(display_name.strip()) < 2:
        request.session["categories_error"] = "Название должно содержать минимум 2 символа"
        return RedirectResponse(url=f"/admin/categories/edit/{category_id}", status_code=302)
    
    # Проверяем формат цвета
    if color and not color.startswith('#'):
        color = f"#{color.lstrip('#')}"
    
    if color and len(color) != 7:
        request.session["categories_error"] = "Цвет должен быть в формате #RRGGBB"
        return RedirectResponse(url=f"/admin/categories/edit/{category_id}", status_code=302)
    
    # Обновляем категорию
    success = await service_category_management.update_category(
        session,
        category_id,
        current_user.id,
        name=name,
        display_name=display_name,
        description=description,
        color=color,
        icon=icon,
        is_active=is_active,
        sort_order=sort_order
    )
    
    if success:
        request.session["categories_message"] = f"Категория '{display_name}' успешно обновлена"
    else:
        request.session["categories_error"] = "Ошибка при обновлении категории (возможно, имя уже существует)"
    
    return RedirectResponse(url=f"/admin/categories/edit/{category_id}", status_code=302)


@categories_router.post("/toggle/{category_id}", response_class=RedirectResponse)
async def toggle_category_status(
    request: Request,
    category_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Переключить статус активности категории"""
    success = await service_category_management.toggle_category_status(
        session, category_id, current_user.id
    )
    
    if success:
        request.session["categories_message"] = "Статус категории изменен"
    else:
        request.session["categories_error"] = "Ошибка при изменении статуса"
    
    return RedirectResponse(url="/admin/categories/", status_code=302)


@categories_router.post("/delete/{category_id}", response_class=RedirectResponse)
async def delete_category(
    request: Request,
    category_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Удалить категорию"""
    success = await service_category_management.delete_category(
        session, category_id, current_user.id
    )
    
    if success:
        request.session["categories_message"] = "Категория удалена"
    else:
        request.session["categories_error"] = "Ошибка при удалении категории (возможно, есть связанные услуги)"
    
    return RedirectResponse(url="/admin/categories/", status_code=302)





