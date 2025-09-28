"""
Роуты для просмотра системных логов (только для администраторов)
"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Request, Query, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import json
from io import StringIO

from ....domain.services.system_logs_service import system_logs_service
from ....domain.entities.system_log import LogLevel
from ....domain.entities.admin_user import AdminUser
from ....infrastructure.database.connection import get_session
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from .admin import require_admin_only

# Настройка шаблонов
templates = Jinja2Templates(directory="src/presentation/templates")

# Роутер для логов
logs_router = APIRouter(prefix="/admin/logs", tags=["logs"])


@logs_router.get("/", response_class=HTMLResponse)
async def logs_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    errors_only: bool = Query(False),
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """
    Страница со списком системных логов (только для администраторов)
    """
    
    # Парсим уровень лога
    level_filter = None
    if level:
        try:
            level_filter = LogLevel(level)
        except ValueError:
            level_filter = None
    
    # Получаем логи
    logs, total_count = await system_logs_service.get_logs(
        session,
        page=page,
        page_size=page_size,
        level_filter=level_filter,
        search_query=search,
        date_from=date_from,
        date_to=date_to,
        module_filter=module,
        show_only_errors=errors_only
    )
    
    # Статистика
    stats = await system_logs_service.get_log_statistics(session, days=7)
    
    # Доступные модули для фильтрации
    available_modules = await system_logs_service.get_available_modules(session)
    
    # Пагинация
    total_pages = (total_count + page_size - 1) // page_size
    has_prev = page > 1
    has_next = page < total_pages
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Системные логи",
        "logs": logs,
        "total_count": total_count,
        "stats": stats,
        "available_modules": available_modules,
        "log_levels": LogLevel,
        # Фильтры
        "current_page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "level_filter": level,
        "search": search or "",
        "module_filter": module or "",
        "date_from": date_from,
        "date_to": date_to,
        "errors_only": errors_only,
        # Сообщения
        "message": request.session.pop("logs_message", None),
        "error": request.session.pop("logs_error", None),
    }
    return templates.TemplateResponse("admin/logs_list.html", context)


@logs_router.get("/view/{log_id}", response_class=HTMLResponse)
async def log_detail(
    request: Request,
    log_id: int,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """
    Детальный просмотр конкретного лога
    """
    log_entry = await system_logs_service.get_log_by_id(session, log_id)
    if not log_entry:
        raise HTTPException(status_code=404, detail="Лог не найден")
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": f"Лог #{log_id}",
        "log_entry": log_entry,
    }
    return templates.TemplateResponse("admin/logs_detail.html", context)


@logs_router.get("/export/csv")
async def export_logs_csv(
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    errors_only: bool = Query(False),
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """
    Экспорт логов в CSV
    """
    
    # Парсим уровень лога
    level_filter = None
    if level:
        try:
            level_filter = LogLevel(level)
        except ValueError:
            level_filter = None
    
    # Получаем логи (без пагинации для экспорта)
    logs, total_count = await system_logs_service.get_logs(
        session,
        page=1,
        page_size=10000,  # Большой лимит для экспорта
        level_filter=level_filter,
        search_query=search,
        date_from=date_from,
        date_to=date_to,
        module_filter=module,
        show_only_errors=errors_only
    )
    
    # Создаем CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        "ID", "Время", "Уровень", "Модуль", "Функция", "Строка", "Сообщение"
    ])
    
    # Данные
    for log_entry in logs:
        writer.writerow([
            log_entry.id,
            log_entry.formatted_timestamp,
            log_entry.level.value,
            log_entry.module,
            log_entry.function,
            log_entry.line_number,
            log_entry.message
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    # Логируем экспорт
    await hybrid_logger.info(f"Администратор {current_user.username} экспортировал {len(logs)} логов в CSV")
    
    # Возвращаем файл
    filename = f"logs_export_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@logs_router.get("/export/json")
async def export_logs_json(
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    errors_only: bool = Query(False),
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """
    Экспорт логов в JSON
    """
    
    # Парсим уровень лога
    level_filter = None
    if level:
        try:
            level_filter = LogLevel(level)
        except ValueError:
            level_filter = None
    
    # Получаем логи
    logs, total_count = await system_logs_service.get_logs(
        session,
        page=1,
        page_size=10000,
        level_filter=level_filter,
        search_query=search,
        date_from=date_from,
        date_to=date_to,
        module_filter=module,
        show_only_errors=errors_only
    )
    
    # Конвертируем в JSON-совместимый формат
    logs_data = []
    for log_entry in logs:
        logs_data.append({
            "id": log_entry.id,
            "timestamp": log_entry.timestamp.isoformat(),
            "level": log_entry.level.value,
            "module": log_entry.module,
            "function": log_entry.function,
            "line_number": log_entry.line_number,
            "message": log_entry.message,
            "location": log_entry.location,
            "extra_data": log_entry.extra_data
        })
    
    export_data = {
        "export_date": date.today().isoformat(),
        "total_logs": len(logs_data),
        "filters": {
            "level": level,
            "search": search,
            "module": module,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "errors_only": errors_only
        },
        "logs": logs_data
    }
    
    json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    # Логируем экспорт
    await hybrid_logger.info(f"Администратор {current_user.username} экспортировал {len(logs)} логов в JSON")
    
    # Возвращаем файл
    filename = f"logs_export_{date.today().isoformat()}.json"
    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@logs_router.post("/cleanup")
async def cleanup_old_logs(
    request: Request,
    current_user: AdminUser = Depends(require_admin_only),
    session: AsyncSession = Depends(get_session)
):
    """
    Очистка старых логов (только для администраторов)
    """
    deleted_count = 0
    try:
        # Получаем days_to_keep из URL параметров
        days_to_keep = int(request.query_params.get('days_to_keep', 30))
        
        # Валидация
        if days_to_keep < 7 or days_to_keep > 365:
            return {"status": "error", "message": "Количество дней должно быть от 7 до 365", "deleted_count": 0}
        
        deleted_count = await system_logs_service.delete_old_logs(session, days_to_keep)
        
        if deleted_count > 0:
            request.session["logs_message"] = f"Удалено {deleted_count} старых логов (старше {days_to_keep} дней)"
            await hybrid_logger.info(f"Администратор {current_user.username} очистил {deleted_count} старых логов")
        else:
            request.session["logs_message"] = "Старых логов для удаления не найдено"
            
        return {"status": "success", "deleted_count": deleted_count}
            
    except Exception as e:
        request.session["logs_error"] = f"Ошибка при очистке логов: {e}"
        await hybrid_logger.error(f"Ошибка очистки логов администратором {current_user.username}: {e}")
        return {"status": "error", "message": str(e), "deleted_count": 0}
