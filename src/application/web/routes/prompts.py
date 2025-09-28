"""
Роуты для управления промптами
"""
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.services.prompt_management import PromptManagementService
from ....domain.entities.admin_user import AdminUser
from ....infrastructure.database.connection import get_session
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from .admin import require_manager_or_admin

# Настройка шаблонов
templates = Jinja2Templates(directory="src/presentation/templates")

# Роутер для промптов
prompts_router = APIRouter(prefix="/admin/prompts", tags=["prompts"])

# Инициализация сервиса
prompt_service = PromptManagementService()


@prompts_router.get("/", response_class=HTMLResponse)
async def prompts_list(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Список всех промптов"""
    prompts = await prompt_service.get_all_prompts(session)
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Управление промптами",
        "prompts": prompts
    }
    return templates.TemplateResponse("admin/prompts_list.html", context)


@prompts_router.get("/edit/{prompt_id}", response_class=HTMLResponse)
async def prompt_edit_page(
    request: Request,
    prompt_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница редактирования промпта"""
    prompt = await prompt_service.get_prompt_by_id(session, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Промпт не найден")
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": f"Редактирование: {prompt.display_name}",
        "prompt": prompt,
        "error": request.session.pop("prompt_error", None),
        "success": request.session.pop("prompt_success", None)
    }
    return templates.TemplateResponse("admin/prompts_edit.html", context)


@prompts_router.post("/edit/{prompt_id}", response_class=HTMLResponse)
async def prompt_edit_post(
    request: Request,
    prompt_id: int,
    content: str = Form(...),
    display_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    reason: Optional[str] = Form(None),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Обработка редактирования промпта"""
    
    # Валидация контента
    if len(content.strip()) < 10:
        request.session["prompt_error"] = "Промпт должен содержать минимум 10 символов"
        return RedirectResponse(url=f"/admin/prompts/edit/{prompt_id}", status_code=302)
    
    if len(content) > 10000:
        request.session["prompt_error"] = "Промпт не может быть длиннее 10,000 символов"
        return RedirectResponse(url=f"/admin/prompts/edit/{prompt_id}", status_code=302)
    
    # Валидация метаданных
    if display_name and len(display_name.strip()) > 255:
        request.session["prompt_error"] = "Название не может быть длиннее 255 символов"
        return RedirectResponse(url=f"/admin/prompts/edit/{prompt_id}", status_code=302)
    
    # Обновляем промпт
    success = await prompt_service.update_prompt(
        session, 
        prompt_id, 
        content.strip(),
        current_user.id,
        display_name.strip() if display_name else None,
        description.strip() if description else None,
        reason
    )
    
    if success:
        request.session["prompt_success"] = "Промпт успешно обновлен"
        await hybrid_logger.info(f"Пользователь {current_user.username} обновил промпт ID {prompt_id}")
    else:
        request.session["prompt_error"] = "Ошибка при обновлении промпта"
    
    return RedirectResponse(url=f"/admin/prompts/edit/{prompt_id}", status_code=302)


@prompts_router.get("/create", response_class=HTMLResponse)
async def prompt_create_page(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Страница создания нового промпта"""
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Создание нового промпта",
        "error": request.session.pop("prompt_error", None),
        "success": request.session.pop("prompt_success", None)
    }
    return templates.TemplateResponse("admin/prompts_create.html", context)


@prompts_router.post("/create", response_class=HTMLResponse)
async def prompt_create_post(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
    display_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Обработка создания нового промпта"""
    
    # Валидация
    if len(name.strip()) < 3:
        request.session["prompt_error"] = "Название должно содержать минимум 3 символа"
        return RedirectResponse(url="/admin/prompts/create", status_code=302)
    
    if len(content.strip()) < 10:
        request.session["prompt_error"] = "Промпт должен содержать минимум 10 символов"
        return RedirectResponse(url="/admin/prompts/create", status_code=302)
    
    # Проверяем, что промпт с таким именем не существует
    existing = await prompt_service.get_prompt_by_name(session, name.strip())
    if existing:
        request.session["prompt_error"] = "Промпт с таким именем уже существует"
        return RedirectResponse(url="/admin/prompts/create", status_code=302)
    
    # Создаем промпт
    new_prompt = await prompt_service.create_prompt(
        session,
        name.strip(),
        content.strip(),
        current_user.id,
        display_name.strip() if display_name else None,
        description.strip() if description else None
    )
    
    if new_prompt:
        request.session["prompt_success"] = "Промпт успешно создан"
        await hybrid_logger.info(f"Пользователь {current_user.username} создал новый промпт '{name}'")
        return RedirectResponse(url=f"/admin/prompts/edit/{new_prompt.id}", status_code=302)
    else:
        request.session["prompt_error"] = "Ошибка при создании промпта"
        return RedirectResponse(url="/admin/prompts/create", status_code=302)


@prompts_router.post("/initialize", response_class=HTMLResponse)
async def initialize_default_prompts(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """Инициализация промптов по умолчанию (только если их нет)"""
    try:
        await prompt_service.initialize_default_prompts(session)
        request.session["prompt_success"] = "Промпты по умолчанию инициализированы"
        await hybrid_logger.info(f"Пользователь {current_user.username} инициализировал промпты по умолчанию")
    except Exception as e:
        request.session["prompt_error"] = "Ошибка инициализации промптов"
        await hybrid_logger.error(f"Ошибка инициализации промптов: {e}")
    
    return RedirectResponse(url="/admin/prompts/", status_code=302)
