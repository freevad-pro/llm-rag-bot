"""
Роуты для управления базой данных (только для администраторов)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text
from typing import List, Optional, Dict, Any
import csv
import io
from datetime import datetime

from ....infrastructure.database.connection import get_session
from .admin import require_admin_user
from ....infrastructure.database.models import (
    User, Lead, Conversation, Message, AdminUser
)
from ....presentation.template_config import templates

router = APIRouter(prefix="/admin/database", tags=["database"])


# Конфигурация таблиц для управления
MANAGEABLE_TABLES = {
    "users": {
        "model": User,
        "name": "Пользователи",
        "fields": {
            "id": {"name": "ID", "type": "readonly"},
            "chat_id": {"name": "Chat ID", "type": "number", "required": True},
            "telegram_user_id": {"name": "Telegram User ID", "type": "number"},
            "username": {"name": "Username", "type": "text"},
            "first_name": {"name": "Имя", "type": "text"},
            "last_name": {"name": "Фамилия", "type": "text"},
            "phone": {"name": "Телефон", "type": "text"},
            "email": {"name": "Email", "type": "email"},
            "created_at": {"name": "Создан", "type": "readonly"}
        },
        "display_fields": ["id", "chat_id", "username", "first_name", "last_name", "phone", "email", "created_at"],
        "search_fields": ["username", "first_name", "last_name"]
    },
    "leads": {
        "model": Lead,
        "name": "Лиды",
        "fields": {
            "id": {"name": "ID", "type": "readonly"},
            "user_id": {"name": "User ID", "type": "number"},
            "name": {"name": "Имя", "type": "text"},
            "phone": {"name": "Телефон", "type": "text"},
            "email": {"name": "Email", "type": "email"},
            "telegram": {"name": "Telegram", "type": "text"},
            "company": {"name": "Компания", "type": "text"},
            "question": {"name": "Вопрос", "type": "textarea"},
            "status": {"name": "Статус", "type": "text"},
            "sync_attempts": {"name": "Попытки синхронизации", "type": "number"},
            "zoho_lead_id": {"name": "Zoho Lead ID", "type": "text"},
            "last_sync_attempt": {"name": "Последняя синхронизация", "type": "readonly"},
            "auto_created": {"name": "Автосоздан", "type": "boolean"},
            "lead_source": {"name": "Источник лида", "type": "text"},
            "created_at": {"name": "Создан", "type": "readonly"}
        },
        "display_fields": ["id", "name", "phone", "email", "company", "status", "sync_attempts", "created_at"],
        "search_fields": ["name", "phone", "email", "company"]
    },
    "conversations": {
        "model": Conversation,
        "name": "Диалоги",
        "fields": {
            "id": {"name": "ID", "type": "readonly"},
            "chat_id": {"name": "Chat ID", "type": "number"},
            "user_id": {"name": "User ID", "type": "number"},
            "status": {"name": "Статус", "type": "text"},
            "platform": {"name": "Платформа", "type": "text"},
            "extra_data": {"name": "Дополнительные данные", "type": "textarea"},
            "created_at": {"name": "Создан", "type": "readonly"},
            "ended_at": {"name": "Завершен", "type": "readonly"}
        },
        "display_fields": ["id", "chat_id", "user_id", "status", "platform", "created_at", "ended_at"],
        "search_fields": ["status", "platform"]
    }
}


@router.get("/", response_class=HTMLResponse)
async def database_viewer(
    request: Request,
    table: str = "users",
    page: int = 1,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Главная страница управления базой данных
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    # Проверяем что таблица существует
    if table not in MANAGEABLE_TABLES:
        table = "users"
    
    table_config = MANAGEABLE_TABLES[table]
    model = table_config["model"]
    
    # Параметры пагинации
    per_page = 20
    offset = (page - 1) * per_page
    
    # Базовый запрос
    query = select(model)
    
    # Добавляем поиск если указан
    if search:
        search_conditions = []
        for field in table_config["search_fields"]:
            if hasattr(model, field):
                attr = getattr(model, field)
                search_conditions.append(attr.ilike(f"%{search}%"))
        
        if search_conditions:
            from sqlalchemy import or_
            query = query.where(or_(*search_conditions))
    
    # Подсчет общего количества записей
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar()
    
    # Получаем записи с пагинацией
    query = query.order_by(desc(model.id)).offset(offset).limit(per_page)
    result = await session.execute(query)
    records = result.scalars().all()
    
    # Вычисляем параметры пагинации
    total_pages = (total_count + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return templates.TemplateResponse(
        "admin/database_viewer.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": f"База данных - {table_config['name']}",
            "tables": MANAGEABLE_TABLES,
            "current_table": table,
            "table_config": table_config,
            "records": records,
            "search": search or "",
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next
            }
        }
    )


@router.get("/edit/{table}/{record_id}", response_class=HTMLResponse)
async def edit_record_form(
    request: Request,
    table: str,
    record_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Форма редактирования записи
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    # Проверяем что таблица существует
    if table not in MANAGEABLE_TABLES:
        raise HTTPException(status_code=404, detail="Таблица не найдена")
    
    table_config = MANAGEABLE_TABLES[table]
    model = table_config["model"]
    
    # Получаем запись
    query = select(model).where(model.id == record_id)
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    return templates.TemplateResponse(
        "admin/database_edit.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": f"Редактирование - {table_config['name']}",
            "table": table,
            "table_config": table_config,
            "record": record,
            "record_id": record_id
        }
    )


@router.post("/edit/{table}/{record_id}")
async def update_record(
    table: str,
    record_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Обновление записи
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    # Проверяем что таблица существует
    if table not in MANAGEABLE_TABLES:
        raise HTTPException(status_code=404, detail="Таблица не найдена")
    
    table_config = MANAGEABLE_TABLES[table]
    model = table_config["model"]
    
    # Получаем запись
    query = select(model).where(model.id == record_id)
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Получаем данные формы
    form_data = await request.form()
    
    # Обновляем поля
    updated_fields = []
    for field_name, field_config in table_config["fields"].items():
        if field_config["type"] == "readonly":
            continue
            
        if field_name in form_data:
            old_value = getattr(record, field_name)
            new_value = form_data[field_name]
            
            # Конвертируем типы
            if field_config["type"] == "boolean":
                new_value = new_value.lower() in ("true", "1", "on", "yes")
            elif field_config["type"] == "number":
                new_value = int(new_value) if new_value else None
            elif field_config["type"] in ("text", "email", "textarea", "select"):
                new_value = new_value if new_value else None
            
            # Обновляем если значение изменилось
            if old_value != new_value:
                setattr(record, field_name, new_value)
                updated_fields.append(f"{field_name}: {old_value} → {new_value}")
    
    # Сохраняем изменения
    if updated_fields:
        await session.commit()
        
        # Логируем изменения
        from ....infrastructure.logging.hybrid_logger import hybrid_logger
        await hybrid_logger.business(
            f"Администратор {current_user.username} обновил запись {table}#{record_id}: {', '.join(updated_fields)}",
            metadata={
                "admin_id": current_user.id,
                "table": table,
                "record_id": record_id,
                "updated_fields": updated_fields
            }
        )
    
    return RedirectResponse(
        url=f"/admin/database?table={table}&success=updated",
        status_code=303
    )


@router.post("/delete/{table}/{record_id}")
async def delete_record(
    table: str,
    record_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Удаление записи
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    # Проверяем что таблица существует
    if table not in MANAGEABLE_TABLES:
        raise HTTPException(status_code=404, detail="Таблица не найдена")
    
    table_config = MANAGEABLE_TABLES[table]
    model = table_config["model"]
    
    # Получаем запись
    query = select(model).where(model.id == record_id)
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Логируем удаление перед удалением
    from ....infrastructure.logging.hybrid_logger import hybrid_logger
    await hybrid_logger.warning(
        f"Администратор {current_user.username} удалил запись {table}#{record_id}",
        metadata={
            "admin_id": current_user.id,
            "table": table,
            "record_id": record_id,
            "record_data": {field: getattr(record, field) for field in table_config["display_fields"] if hasattr(record, field)}
        }
    )
    
    # Удаляем запись
    await session.delete(record)
    await session.commit()
    
    return {"success": True}


@router.get("/export/{table}")
async def export_table_csv(
    table: str,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Экспорт таблицы в CSV
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Доступ только для администраторов"
        )
    
    # Проверяем что таблица существует
    if table not in MANAGEABLE_TABLES:
        raise HTTPException(status_code=404, detail="Таблица не найдена")
    
    table_config = MANAGEABLE_TABLES[table]
    model = table_config["model"]
    
    # Базовый запрос
    query = select(model)
    
    # Добавляем поиск если указан
    if search:
        search_conditions = []
        for field in table_config["search_fields"]:
            if hasattr(model, field):
                attr = getattr(model, field)
                search_conditions.append(attr.ilike(f"%{search}%"))
        
        if search_conditions:
            from sqlalchemy import or_
            query = query.where(or_(*search_conditions))
    
    # Получаем все записи
    query = query.order_by(desc(model.id))
    result = await session.execute(query)
    records = result.scalars().all()
    
    # Создаем CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    headers = [table_config["fields"][field]["name"] for field in table_config["display_fields"]]
    writer.writerow(headers)
    
    # Данные
    for record in records:
        row = []
        for field in table_config["display_fields"]:
            value = getattr(record, field, "")
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            elif value is None:
                value = ""
            row.append(str(value))
        writer.writerow(row)
    
    # Логируем экспорт
    from ....infrastructure.logging.hybrid_logger import hybrid_logger
    await hybrid_logger.business(
        f"Администратор {current_user.username} экспортировал таблицу {table} ({len(records)} записей)",
        metadata={
            "admin_id": current_user.id,
            "table": table,
            "records_count": len(records),
            "search": search
        }
    )
    
    # Возвращаем CSV файл
    output.seek(0)
    filename = f"{table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
