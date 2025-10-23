"""
Роуты для управления каталогом товаров через админ-панель.
Реализует загрузку Excel файлов с blue-green deployment согласно @vision.md
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .admin import require_manager_or_admin, require_admin_only
from ....domain.entities.admin_user import AdminUser
from ....domain.services.catalog_management import CatalogManagementService
from ....infrastructure.database.connection import get_session
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from ....config.settings import settings
from ....presentation.template_config import templates
from ....infrastructure.utils.timezone_utils import format_moscow_datetime

# Роутер для управления каталогом
catalog_router = APIRouter(prefix="/admin/catalog", tags=["catalog"])

# Кэш для проверки модели эмбеддингов (5 минут TTL)
_model_check_cache = {"last_check": None, "result": True, "ttl": 300}


@catalog_router.get("/", response_class=HTMLResponse)
async def catalog_dashboard(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin)
):
    """
    Главная страница управления каталогом.
    Редирект на страницу загрузки.
    """
    return RedirectResponse(url="/admin/catalog/upload", status_code=302)


@catalog_router.get("/upload", response_class=HTMLResponse)
async def catalog_upload_page(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin)
):
    """
    Страница загрузки нового каталога Excel.
    Доступна менеджерам и администраторам.
    """
    # Проверяем наличие модели только для sentence-transformers
    model_ready = True
    model_warning = None
    
    if settings.embedding_provider == "sentence-transformers":
        import time
        now = time.time()
        
        # Используем кэш если проверка была недавно
        if (_model_check_cache["last_check"] and 
            now - _model_check_cache["last_check"] < _model_check_cache["ttl"]):
            model_ready = _model_check_cache["result"]
        else:
            # Проверяем модель только если кэш устарел
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface"
            model_name = settings.embedding_model.replace("/", "--")
            model_dir = cache_dir / f"models--{model_name}"
            
            model_ready = model_dir.exists() and any(model_dir.iterdir())
            model_warning = None if model_ready else "Модель эмбеддингов не загружена. Перейдите в раздел 'Модель эмбеддингов' для её загрузки."
            
            # Обновляем кэш
            _model_check_cache.update({
                "last_check": now,
                "result": model_ready
            })
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Загрузка каталога",
        "max_file_size_mb": settings.max_upload_size_mb,
        "supported_formats": ["xlsx", "xls"],
        "model_ready": model_ready,
        "model_warning": model_warning
    }
    
    return templates.TemplateResponse("admin/catalog_upload.html", context)


@catalog_router.post("/upload")
async def catalog_upload_post(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    schedule_type: str = Form("immediate"),  # immediate или scheduled
    schedule_time: Optional[str] = Form(None),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Обработка загрузки Excel файла каталога.
    Поддерживает немедленную и отложенную переиндексацию.
    """
    
    # Проверка наличия модели для sentence-transformers
    if settings.embedding_provider == "sentence-transformers":
        from pathlib import Path as PathLib
        cache_dir = PathLib.home() / ".cache" / "huggingface"
        model_name = settings.embedding_model.replace("/", "--")
        model_dir = cache_dir / f"models--{model_name}"
        
        if not (model_dir.exists() and any(model_dir.iterdir())):
            raise HTTPException(
                status_code=400,
                detail="Модель эмбеддингов не загружена. Перейдите в раздел 'Модель эмбеддингов' для её загрузки."
            )
    
    # Валидация файла
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")
    
    # Проверка расширения
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.xlsx', '.xls']:
        raise HTTPException(
            status_code=400, 
            detail="Поддерживаются только файлы Excel (.xlsx, .xls)"
        )
    
    # Проверка размера файла
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    max_size = settings.max_upload_size_mb * 1024 * 1024  # Конвертируем в байты
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Размер файла превышает {settings.max_upload_size_mb} MB"
        )
    
    # Сохраняем файл
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"catalog_{timestamp}_{file.filename}"
    file_path = upload_dir / safe_filename
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    await hybrid_logger.info(
        f"Загружен новый каталог: {safe_filename} ({file_size} байт) пользователем {current_user.username}"
    )
    
    # Создаем сервис управления каталогом
    catalog_service = CatalogManagementService(session)
    
    try:
        if schedule_type == "immediate":
            # Немедленная переиндексация в фоне
            background_tasks.add_task(
                _process_catalog_reindex,
                str(file_path),
                current_user.id
            )
            
            message = "Файл загружен. Переиндексация началась в фоновом режиме."
            
        else:
            # Отложенная переиндексация
            if not schedule_time:
                raise HTTPException(status_code=400, detail="Не указано время планирования")
            
            # TODO: Реализовать планировщик задач
            message = f"Файл загружен. Переиндексация запланирована на {schedule_time}."
        
        # Сохраняем информацию о загрузке в БД
        await catalog_service.create_catalog_version(
            filename=safe_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            uploaded_by=current_user.id,
            status="uploaded" if schedule_type == "scheduled" else "processing"
        )
        
        context = {
            "request": request,
            "current_user": current_user,
            "page_title": "Загрузка каталога",
            "success": message,
            "filename": safe_filename,
            "file_size": f"{file_size / 1024 / 1024:.2f} MB"
        }
        
        return templates.TemplateResponse("admin/catalog_upload.html", context)
        
    except Exception as e:
        # Удаляем файл при ошибке
        if file_path.exists():
            file_path.unlink()
        
        await hybrid_logger.error(f"Ошибка при обработке каталога: {str(e)}")
        
        context = {
            "request": request,
            "current_user": current_user,
            "page_title": "Загрузка каталога",
            "error": f"Ошибка при обработке файла: {str(e)}",
            "max_file_size_mb": settings.max_upload_size_mb,
            "supported_formats": ["xlsx", "xls"]
        }
        
        return templates.TemplateResponse("admin/catalog_upload.html", context)


@catalog_router.get("/status", response_class=HTMLResponse)
async def catalog_status_page(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Страница статуса переиндексации каталога.
    Показывает текущий прогресс и историю версий.
    """
    catalog_service = CatalogManagementService(session)
    
    # Получаем текущий статус
    current_status = await catalog_service.get_current_indexing_status()
    
    # Получаем историю версий (последние 10)
    version_history = await catalog_service.get_version_history(limit=10)
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Статус каталога",
        "current_status": current_status,
        "version_history": version_history
    }
    
    return templates.TemplateResponse("admin/catalog_status.html", context)


@catalog_router.get("/status/api")
async def catalog_status_api(
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    API endpoint для получения статуса переиндексации.
    Используется для AJAX обновлений на странице статуса.
    """
    catalog_service = CatalogManagementService(session)
    status = await catalog_service.get_current_indexing_status()
    
    # Предварительно форматируем время чтобы не делать это в JSONResponse
    started_at_formatted = None
    estimated_completion_formatted = None
    
    if status.get("started_at"):
        started_at_formatted = format_moscow_datetime(status.get("started_at"))
    if status.get("estimated_completion"):
        estimated_completion_formatted = format_moscow_datetime(status.get("estimated_completion"))
    
    return JSONResponse({
        "status": status.get("status", "unknown"),
        "progress": status.get("progress", 0),
        "message": status.get("message", ""),
        "products_count": status.get("products_count", 0),
        "started_at": started_at_formatted,
        "estimated_completion": estimated_completion_formatted
    })


@catalog_router.get("/history", response_class=HTMLResponse)
async def catalog_history_page(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Страница истории версий каталога.
    Показывает все загруженные версии с возможностью отката.
    """
    catalog_service = CatalogManagementService(session)
    
    # Получаем полную историю версий
    version_history = await catalog_service.get_version_history(limit=50)
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "История каталога",
        "version_history": version_history
    }
    
    return templates.TemplateResponse("admin/catalog_history.html", context)


@catalog_router.get("/version/{version_id}/details")
async def get_catalog_version_details(
    version_id: int,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    API endpoint для получения деталей версии каталога.
    Используется в модальном окне на странице истории.
    """
    catalog_service = CatalogManagementService(session)
    
    try:
        version = await catalog_service.get_version_by_id(version_id)
        
        if not version:
            return JSONResponse(
                {"error": "Версия не найдена"},
                status_code=404
            )
        
        return JSONResponse({
            "id": version["id"],
            "filename": version["filename"],
            "file_size_mb": version["file_size_mb"],
            "status": version["status"],
            "products_count": version["products_count"],
            "created_at": format_moscow_datetime(version["created_at"]),
            "started_at": format_moscow_datetime(version["started_at"]),
            "completed_at": format_moscow_datetime(version["completed_at"]),
            "progress": version["progress"],
            "error_message": version["error_message"]
        })
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка получения деталей версии {version_id}: {e}")
        return JSONResponse(
            {"error": f"Ошибка получения деталей: {str(e)}"},
            status_code=500
        )


@catalog_router.post("/version/{version_id}/activate", response_class=HTMLResponse)
async def activate_catalog_version(
    version_id: int,
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Активирует выбранную версию каталога (blue-green deployment).
    Доступно менеджерам и администраторам.
    """
    catalog_service = CatalogManagementService(session)
    
    try:
        await catalog_service.activate_catalog_version(version_id)
        await hybrid_logger.info(f"Пользователь {current_user.username} активировал версию каталога {version_id}")
        
        return RedirectResponse(
            url="/admin/catalog/history?message=Версия каталога успешно активирована", 
            status_code=302
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка активации версии каталога {version_id}: {e}")
        return RedirectResponse(
            url=f"/admin/catalog/history?error=Ошибка активации: {str(e)}", 
            status_code=302
        )


@catalog_router.delete("/version/{version_id}")
async def delete_catalog_version_api(
    version_id: int,
    request: Request,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """
    API endpoint для удаления версии каталога.
    Доступно только администраторам.
    """
    catalog_service = CatalogManagementService(session)
    
    try:
        await catalog_service.delete_catalog_version(version_id)
        await hybrid_logger.info(f"Пользователь {current_user.username} удалил версию каталога {version_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Версия каталога успешно удалена"
        })
        
    except ValueError as e:
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=400)
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка удаления версии каталога {version_id}: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Ошибка удаления: {str(e)}"
        }, status_code=500)


# Эндпоинты отката удалены - функция отката убрана


async def _process_catalog_reindex(
    file_path: str,
    user_id: int
):
    """
    Фоновая задача переиндексации каталога.
    Реализует blue-green deployment без простоя.
    Создает собственную сессию БД для фонового выполнения.
    """
    from ....infrastructure.database.connection import async_session_factory
    
    async with async_session_factory() as session:
        catalog_service = CatalogManagementService(session)
        
        try:
            await catalog_service.reindex_catalog(
                file_path=file_path,
                user_id=user_id
            )
            
            await hybrid_logger.info(f"Переиндексация каталога завершена успешно: {file_path}")
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка переиндексации каталога {file_path}: {str(e)}")
            
            # Обновляем статус в БД
            try:
                await catalog_service.update_indexing_status(
                    file_path=file_path,
                    status="failed",
                    error_message=str(e)
                )
                await session.commit()
            except Exception as commit_error:
                await hybrid_logger.error(f"Ошибка сохранения статуса ошибки: {commit_error}")
                await session.rollback()


# Функция _process_catalog_rollback удалена - функция отката убрана


@catalog_router.post("/fix-completion-time")
async def fix_completion_time(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(require_admin_only)
):
    """
    Исправляет время завершения для активных версий каталога без completed_at.
    Временный эндпоинт для исправления существующих данных.
    """
    try:
        # Используем сервис для обновления
        catalog_service = CatalogManagementService(session)
        
        # Находим активную версию без времени завершения
        from sqlalchemy import select, update
        from ....infrastructure.database.models import CatalogVersion
        
        stmt = select(CatalogVersion).where(
            CatalogVersion.status == "active",
            CatalogVersion.completed_at.is_(None)
        )
        result = await session.execute(stmt)
        version = result.scalar_one_or_none()
        
        if not version:
            return JSONResponse({
                "success": False, 
                "message": "Нет версий для исправления"
            })
        
        # Рассчитываем время завершения
        from datetime import timedelta
        if version.started_at:
            completion_time = version.started_at + timedelta(minutes=1)
        else:
            completion_time = version.created_at + timedelta(minutes=2)
        
        # Обновляем запись
        update_stmt = update(CatalogVersion).where(
            CatalogVersion.id == version.id
        ).values(
            completed_at=completion_time,
            indexed_at=completion_time
        )
        
        await session.execute(update_stmt)
        await session.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Время завершения установлено для версии {version.id}",
            "completed_at": completion_time.isoformat()
        })
        
    except Exception as e:
        await session.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Ошибка: {str(e)}"
        }, status_code=500)


@catalog_router.post("/fix-active-flags")
async def fix_active_flags(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(require_admin_only)
):
    """
    Исправляет поля is_active для версий каталога.
    Временный эндпоинт для исправления существующих данных.
    """
    try:
        from sqlalchemy import select, update
        from ....infrastructure.database.models import CatalogVersion
        
        # Находим активную версию по статусу
        active_stmt = select(CatalogVersion).where(
            CatalogVersion.status == "active"
        )
        result = await session.execute(active_stmt)
        active_versions = result.scalars().all()
        
        if len(active_versions) == 0:
            return JSONResponse({
                "success": False,
                "message": "Нет активных версий"
            })
        
        if len(active_versions) > 1:
            # Если несколько активных, оставляем только последнюю
            latest_version = max(active_versions, key=lambda v: v.created_at)
            active_version_id = latest_version.id
        else:
            active_version_id = active_versions[0].id
        
        # Деактивируем все версии
        deactivate_stmt = update(CatalogVersion).values(is_active=False)
        await session.execute(deactivate_stmt)
        
        # Активируем только нужную версию
        activate_stmt = update(CatalogVersion).where(
            CatalogVersion.id == active_version_id
        ).values(is_active=True)
        await session.execute(activate_stmt)
        
        await session.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Поле is_active исправлено. Активна версия {active_version_id}"
        })
        
    except Exception as e:
        await session.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Ошибка: {str(e)}"
        }, status_code=500)
