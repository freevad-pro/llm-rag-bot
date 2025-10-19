"""
Роуты админ-панели с классической авторизацией логин/пароль.
Замена Telegram авторизации на username/password.
"""
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..password_auth import password_auth_service
from ....domain.entities.admin_user import AdminUser
from ....infrastructure.database.connection import get_session
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from ....config.settings import settings
from ....presentation.template_config import templates

# Роутер для админ-панели
admin_router = APIRouter(prefix="/admin", tags=["admin"])


async def get_current_admin_user(request: Request, session: AsyncSession = Depends(get_session)) -> Optional[AdminUser]:
    """
    Получение текущего авторизованного пользователя из сессии.
    Используется как dependency.
    """
    user_id = request.session.get("admin_user_id")
    if not user_id:
        return None
    
    return await password_auth_service.get_user_by_id(session, user_id)


def require_admin_user_with_redirect(request: Request):
    """
    Dependency factory для создания функции проверки авторизации с редиректом
    """
    async def _require_admin_user(current_user: Optional[AdminUser] = Depends(get_current_admin_user)) -> AdminUser:
        if not current_user:
            # Для HTML запросов делаем редирект, для API возвращаем JSON
            if request.headers.get("accept", "").startswith("text/html"):
                raise HTTPException(
                    status_code=status.HTTP_302_FOUND,
                    detail="Redirect to login",
                    headers={"Location": "/admin/login"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Требуется авторизация"
                )
        if not current_user.is_active:
            if request.headers.get("accept", "").startswith("text/html"):
                raise HTTPException(
                    status_code=status.HTTP_302_FOUND,
                    detail="Redirect to login",
                    headers={"Location": "/admin/login?error=account_disabled"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Аккаунт деактивирован"
                )
        return current_user
    return _require_admin_user

async def require_admin_user(current_user: Optional[AdminUser] = Depends(get_current_admin_user)) -> AdminUser:
    """
    Требует авторизованного пользователя.
    Возвращает HTTPException если пользователь не авторизован.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    return current_user


async def require_manager_or_admin(current_user: AdminUser = Depends(require_admin_user)) -> AdminUser:
    """Требует роль менеджера или администратора"""
    if not current_user.can_manage_catalog():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user


async def require_admin_only(current_user: AdminUser = Depends(require_admin_user)) -> AdminUser:
    """Требует роль только администратора"""
    if not current_user.is_administrator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов"
        )
    return current_user


@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user)
):
    """
    Главная страница админ-панели.
    Редирект на логин если не авторизован.
    """
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # TODO: Получить статистику системы
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Панель управления",
        "stats": {
            "users_count": 0,  # TODO: реальные данные
            "conversations_count": 0,
            "leads_count": 0,
            "catalog_products": 0,
        }
    }
    
    return templates.TemplateResponse("admin/dashboard.html", context)


@admin_router.get("/login", response_class=HTMLResponse)
async def admin_login_page(
    request: Request,
    current_user: Optional[AdminUser] = Depends(get_current_admin_user)
):
    """
    Страница авторизации через логин/пароль.
    """
    if current_user:
        return RedirectResponse(url="/admin/", status_code=302)
    
    context = {
        "request": request,
        "page_title": "Вход в систему",
    }
    
    return templates.TemplateResponse("admin/login_classic.html", context)


@admin_router.post("/login")
async def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    """Обработка входа через логин/пароль"""
    
    user = await password_auth_service.authenticate_user(session, username, password)
    
    if not user:
        context = {
            "request": request,
            "page_title": "Вход в систему",
            "error": "Неверный логин или пароль",
            "username": username
        }
        return templates.TemplateResponse("admin/login_classic.html", context)
    
    # Сохраняем в сессию
    request.session["admin_user_id"] = user.id
    request.session["admin_username"] = user.username
    
    await hybrid_logger.info(f"Успешный вход пользователя: {username}")
    
    return RedirectResponse(url="/admin/", status_code=302)


@admin_router.get("/logout")
async def admin_logout(request: Request):
    """Выход из системы"""
    username = request.session.get("admin_username", "Unknown")
    request.session.clear()
    
    await hybrid_logger.info(f"Выход пользователя: {username}")
    
    return RedirectResponse(url="/admin/login", status_code=302)


@admin_router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Страница запроса сброса пароля"""
    context = {
        "request": request,
        "page_title": "Восстановление пароля"
    }
    return templates.TemplateResponse("admin/forgot_password.html", context)


@admin_router.post("/forgot-password")
async def forgot_password_post(
    request: Request,
    email: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    """Обработка запроса сброса пароля"""
    
    success = await password_auth_service.initiate_password_reset(session, email)
    
    context = {
        "request": request,
        "page_title": "Восстановление пароля",
        "success": "Если указанный email зарегистрирован, на него отправлена ссылка для сброса пароля."
    }
    
    return templates.TemplateResponse("admin/forgot_password.html", context)


@admin_router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    """Страница установки нового пароля"""
    context = {
        "request": request,
        "page_title": "Новый пароль",
        "token": token
    }
    return templates.TemplateResponse("admin/reset_password.html", context)


@admin_router.post("/reset-password")
async def reset_password_post(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    """Обработка установки нового пароля"""
    
    if password != confirm_password:
        context = {
            "request": request,
            "page_title": "Новый пароль",
            "token": token,
            "error": "Пароли не совпадают"
        }
        return templates.TemplateResponse("admin/reset_password.html", context)
    
    if len(password) < 6:
        context = {
            "request": request,
            "page_title": "Новый пароль",
            "token": token,
            "error": "Пароль должен содержать минимум 6 символов"
        }
        return templates.TemplateResponse("admin/reset_password.html", context)
    
    success = await password_auth_service.reset_password(session, token, password)
    
    if not success:
        context = {
            "request": request,
            "page_title": "Новый пароль",
            "token": token,
            "error": "Недействительный или просроченный токен"
        }
        return templates.TemplateResponse("admin/reset_password.html", context)
    
    # Перенаправляем на страницу входа с сообщением об успехе
    context = {
        "request": request,
        "page_title": "Вход в систему",
        "success": "Пароль успешно изменен. Войдите с новым паролем."
    }
    return templates.TemplateResponse("admin/login_classic.html", context)


@admin_router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: AdminUser = Depends(require_admin_user)
):
    """Страница смены пароля"""
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Смена пароля"
    }
    return templates.TemplateResponse("admin/change_password.html", context)


@admin_router.post("/change-password", response_class=HTMLResponse)
async def change_password_post(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: AdminUser = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Обработка смены пароля"""
    
    if new_password != confirm_password:
        return HTMLResponse("""
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Новые пароли не совпадают
            </div>
        """)
    
    if len(new_password) < 8:
        return HTMLResponse("""
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Новый пароль должен содержать минимум 8 символов
            </div>
        """)
    
    # Проверяем текущий пароль
    auth_user = await password_auth_service.authenticate_user(session, current_user.username, old_password)
    if not auth_user:
        return HTMLResponse("""
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Неверный старый пароль
            </div>
        """)
    
    # Меняем пароль
    success = await password_auth_service.change_password(session, current_user.id, new_password)
    
    if success:
        return HTMLResponse("""
            <div class="alert alert-success" role="alert">
                <i class="bi bi-check-circle"></i>
                Пароль успешно изменен
            </div>
            <script>
                // Очищаем поля формы
                document.getElementById('old_password').value = '';
                document.getElementById('new_password').value = '';
                document.getElementById('confirm_password').value = '';
            </script>
        """)
    else:
        return HTMLResponse("""
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Ошибка при смене пароля
            </div>
        """)


@admin_router.get("/profile", response_class=HTMLResponse)
async def admin_profile(
    request: Request,
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Страница профиля администратора.
    """
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Профиль",
        "error": request.session.pop("change_password_error", None),
        "message": request.session.pop("change_password_message", None)
    }
    
    return templates.TemplateResponse("admin/profile.html", context)


@admin_router.post("/profile/update", response_class=HTMLResponse)
async def update_profile_post(
    request: Request,
    email: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    current_user: AdminUser = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Обновление профиля администратора.
    """
    try:
        # Валидация email
        if not email or "@" not in email:
            return HTMLResponse("""
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle"></i>
                    Введите корректный email адрес
                </div>
            """)
        
        # Обновляем профиль
        success = await password_auth_service.update_profile(
            session, 
            current_user.id, 
            email, 
            first_name, 
            last_name
        )
        
        if success:
            # Обновляем данные в сессии
            current_user.email = email
            current_user.first_name = first_name
            current_user.last_name = last_name
            
            return HTMLResponse("""
                <div class="alert alert-success" role="alert">
                    <i class="bi bi-check-circle"></i>
                    Профиль успешно обновлен
                </div>
                <script>
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                </script>
            """)
        else:
            return HTMLResponse("""
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle"></i>
                    Ошибка при обновлении профиля. Возможно, email уже используется.
                </div>
            """)
            
    except Exception as e:
        await hybrid_logger.error(f"Ошибка обновления профиля: {e}")
        return HTMLResponse("""
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Ошибка при обновлении профиля
            </div>
        """)


@admin_router.get("/debug/config")
async def debug_config():
    """
    Отладочный endpoint для проверки конфигурации (только для разработки).
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    
    return {
        "auth_type": "classic_login_password",
        "smtp_configured": bool(settings.smtp_host and settings.smtp_user),
        "secret_key_set": bool(settings.secret_key),
        "debug": settings.debug,
    }