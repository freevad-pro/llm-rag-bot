"""
Роуты для управления пользователями админ-панели.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
import logging

from ....infrastructure.database.connection import get_session
from ....domain.services.user_management import UserManagementService
from ....domain.entities.admin_user import AdminUser, AdminRole
from .admin import require_admin_only

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])
templates = Jinja2Templates(directory="src/presentation/templates")


@router.get("/", response_class=HTMLResponse)
async def users_list(
    request: Request,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Список всех пользователей"""
    try:
        user_service = UserManagementService(session)
        users = await user_service.get_all_users()
        stats = await user_service.get_user_stats()
        
        # Получаем сообщения из сессии
        messages = request.session.pop('messages', [])
        
        return templates.TemplateResponse(
            "admin/users_list.html",
            {
                "request": request,
                "users": users,
                "stats": stats,
                "current_user": current_user,
                "messages": messages,
                "page_title": "Управление пользователями"
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/create", response_class=HTMLResponse)
async def create_user_page(
    request: Request,
    current_user: AdminUser = Depends(require_admin_only),
):
    """Страница создания нового пользователя"""
    # Получаем сообщения из сессии
    messages = request.session.pop('messages', [])
    
    return templates.TemplateResponse(
        "admin/users_create.html",
        {
            "request": request,
            "current_user": current_user,
            "messages": messages,
            "roles": [role for role in AdminRole],
            "page_title": "Создание пользователя"
        }
    )


@router.post("/create")
async def create_user_post(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    email: Annotated[str, Form()],
    role: Annotated[str, Form()],
    is_active: Annotated[bool, Form()] = True,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Создание нового пользователя"""
    try:
        # Валидация
        if len(username.strip()) < 3:
            request.session['messages'] = [{"type": "error", "text": "Имя пользователя должно содержать минимум 3 символа"}]
            return RedirectResponse(url="/admin/users/create", status_code=status.HTTP_302_FOUND)
        
        if len(password) < 8:
            request.session['messages'] = [{"type": "error", "text": "Пароль должен содержать минимум 8 символов"}]
            return RedirectResponse(url="/admin/users/create", status_code=status.HTTP_302_FOUND)
        
        if "@" not in email:
            request.session['messages'] = [{"type": "error", "text": "Некорректный email адрес"}]
            return RedirectResponse(url="/admin/users/create", status_code=status.HTTP_302_FOUND)
        
        try:
            user_role = AdminRole(role)
        except ValueError:
            request.session['messages'] = [{"type": "error", "text": "Некорректная роль"}]
            return RedirectResponse(url="/admin/users/create", status_code=status.HTTP_302_FOUND)
        
        # Создаем пользователя
        user_service = UserManagementService(session)
        new_user = await user_service.create_user(
            username=username.strip(),
            password=password,
            email=email.strip(),
            role=user_role,
            created_by=current_user.id,
            is_active=is_active
        )
        
        logger.info(f"Пользователь {username} создан администратором {current_user.username}")
        request.session['messages'] = [{"type": "success", "text": f"Пользователь '{username}' успешно создан"}]
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
    except ValueError as e:
        request.session['messages'] = [{"type": "error", "text": str(e)}]
        return RedirectResponse(url="/admin/users/create", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        request.session['messages'] = [{"type": "error", "text": "Ошибка при создании пользователя"}]
        return RedirectResponse(url="/admin/users/create", status_code=status.HTTP_302_FOUND)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_page(
    request: Request,
    user_id: int,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Страница редактирования пользователя"""
    try:
        user_service = UserManagementService(session)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            request.session['messages'] = [{"type": "error", "text": "Пользователь не найден"}]
            return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
        # Получаем сообщения из сессии
        messages = request.session.pop('messages', [])
        
        return templates.TemplateResponse(
            "admin/users_edit.html",
            {
                "request": request,
                "user": user,
                "current_user": current_user,
                "messages": messages,
                "roles": [role for role in AdminRole],
                "page_title": f"Редактирование пользователя: {user.username}"
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
        request.session['messages'] = [{"type": "error", "text": "Ошибка сервера"}]
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.post("/{user_id}/edit")
async def edit_user_post(
    request: Request,
    user_id: int,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    role: Annotated[str, Form()],
    is_active: Annotated[bool, Form()] = True,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Обновление данных пользователя"""
    try:
        # Валидация
        if len(username.strip()) < 3:
            request.session['messages'] = [{"type": "error", "text": "Имя пользователя должно содержать минимум 3 символа"}]
            return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
        
        if "@" not in email:
            request.session['messages'] = [{"type": "error", "text": "Некорректный email адрес"}]
            return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
        
        try:
            user_role = AdminRole(role)
        except ValueError:
            request.session['messages'] = [{"type": "error", "text": "Некорректная роль"}]
            return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
        
        user_service = UserManagementService(session)
        
        # Проверяем возможность изменения роли
        if user_role:
            can_change, reason = await user_service.can_change_role(user_id, user_role, current_user.id)
            if not can_change:
                request.session['messages'] = [{"type": "error", "text": reason}]
                return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
        
        # Обновляем пользователя
        updated_user = await user_service.update_user(
            user_id=user_id,
            updated_by=current_user.id,
            username=username.strip(),
            email=email.strip(),
            role=user_role,
            is_active=is_active
        )
        
        if updated_user:
            logger.info(f"Пользователь {username} обновлен администратором {current_user.username}")
            request.session['messages'] = [{"type": "success", "text": f"Пользователь '{username}' успешно обновлен"}]
            return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        else:
            request.session['messages'] = [{"type": "error", "text": "Пользователь не найден"}]
            return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
    except ValueError as e:
        request.session['messages'] = [{"type": "error", "text": str(e)}]
        return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя {user_id}: {e}")
        request.session['messages'] = [{"type": "error", "text": "Ошибка при обновлении пользователя"}]
        return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)


@router.post("/{user_id}/toggle-status")
async def toggle_user_status(
    request: Request,
    user_id: int,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Переключить статус пользователя (активный/заблокированный)"""
    try:
        user_service = UserManagementService(session)
        
        # Проверяем, что это не сам пользователь
        if user_id == current_user.id:
            request.session['messages'] = [{"type": "error", "text": "Нельзя заблокировать самого себя"}]
            return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
        updated_user = await user_service.toggle_user_status(user_id, current_user.id)
        
        if updated_user:
            status_text = "активирован" if updated_user.is_active else "заблокирован"
            logger.info(f"Пользователь {updated_user.username} {status_text} администратором {current_user.username}")
            request.session['messages'] = [{"type": "success", "text": f"Пользователь '{updated_user.username}' {status_text}"}]
        else:
            request.session['messages'] = [{"type": "error", "text": "Пользователь не найден"}]
        
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса пользователя {user_id}: {e}")
        request.session['messages'] = [{"type": "error", "text": "Ошибка при изменении статуса пользователя"}]
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.post("/{user_id}/change-password")
async def change_user_password(
    request: Request,
    user_id: int,
    new_password: Annotated[str, Form()],
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Принудительная смена пароля пользователя"""
    try:
        if len(new_password) < 8:
            request.session['messages'] = [{"type": "error", "text": "Пароль должен содержать минимум 8 символов"}]
            return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
        
        user_service = UserManagementService(session)
        success = await user_service.change_user_password(user_id, new_password, current_user.id)
        
        if success:
            user = await user_service.get_user_by_id(user_id)
            logger.info(f"Пароль пользователя {user.username if user else user_id} изменен администратором {current_user.username}")
            request.session['messages'] = [{"type": "success", "text": "Пароль успешно изменен"}]
        else:
            request.session['messages'] = [{"type": "error", "text": "Пользователь не найден"}]
        
        return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Ошибка при смене пароля пользователя {user_id}: {e}")
        request.session['messages'] = [{"type": "error", "text": "Ошибка при смене пароля"}]
        return RedirectResponse(url=f"/admin/users/{user_id}/edit", status_code=status.HTTP_302_FOUND)


@router.post("/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """Удаление пользователя"""
    try:
        user_service = UserManagementService(session)
        
        # Проверяем возможность удаления
        can_delete, reason = await user_service.can_delete_user(user_id, current_user.id)
        if not can_delete:
            request.session['messages'] = [{"type": "error", "text": reason}]
            return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
        # Получаем данные пользователя перед удалением
        user = await user_service.get_user_by_id(user_id)
        username = user.username if user else f"ID {user_id}"
        
        # Удаляем пользователя
        success = await user_service.delete_user(user_id)
        
        if success:
            logger.info(f"Пользователь {username} удален администратором {current_user.username}")
            request.session['messages'] = [{"type": "success", "text": f"Пользователь '{username}' успешно удален"}]
        else:
            request.session['messages'] = [{"type": "error", "text": "Пользователь не найден"}]
        
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя {user_id}: {e}")
        request.session['messages'] = [{"type": "error", "text": "Ошибка при удалении пользователя"}]
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
