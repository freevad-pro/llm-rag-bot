"""
Роуты для управления лидами в админ-панели.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
import logging
from datetime import datetime, timedelta

from ....infrastructure.database.connection import get_async_session
from ....domain.services.lead_management import LeadManagementService
from ....domain.entities.admin_user import AdminUser
from .admin import require_admin_user, require_manager_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/leads", tags=["admin-leads"])
templates = Jinja2Templates(directory="src/presentation/templates")


@router.get("/", response_class=HTMLResponse)
async def leads_list(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Список всех лидов с пагинацией и фильтрацией"""
    try:
        lead_service = LeadManagementService(session)
        
        # Получаем лиды с фильтрацией
        leads_data = await lead_service.get_leads_paginated(
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            search=search
        )
        
        # Получаем статистику
        stats = await lead_service.get_leads_stats()
        
        # Получаем сообщения из сессии
        messages = request.session.pop('messages', [])
        
        return templates.TemplateResponse(
            "admin/leads_list.html",
            {
                "request": request,
                "leads": leads_data["leads"],
                "pagination": leads_data["pagination"],
                "stats": stats,
                "current_user": current_user,
                "messages": messages,
                "page_title": "Управление лидами",
                "current_page": page,
                "per_page": per_page,
                "status_filter": status_filter,
                "search": search
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка лидов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/{lead_id}", response_class=HTMLResponse)
async def lead_detail(
    lead_id: int,
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """Детальная информация о лиде"""
    try:
        lead_service = LeadManagementService(session)
        lead = await lead_service.get_lead_by_id(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail="Лид не найден")
        
        # Получаем историю взаимодействий
        interactions = await lead_service.get_lead_interactions(lead_id)
        
        return templates.TemplateResponse(
            "admin/lead_detail.html",
            {
                "request": request,
                "lead": lead,
                "interactions": interactions,
                "current_user": current_user,
                "page_title": f"Лид #{lead_id}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении лида {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.post("/{lead_id}/update-status")
async def update_lead_status(
    lead_id: int,
    request: Request,
    new_status: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """Обновление статуса лида"""
    try:
        lead_service = LeadManagementService(session)
        
        success = await lead_service.update_lead_status(
            lead_id=lead_id,
            new_status=new_status,
            notes=notes,
            updated_by=current_user.id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Лид не найден")
        
        # Добавляем сообщение об успехе
        request.session['messages'] = ['Статус лида успешно обновлен']
        
        return RedirectResponse(
            url=f"/admin/leads/{lead_id}",
            status_code=302
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса лида {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.post("/{lead_id}/add-note")
async def add_lead_note(
    lead_id: int,
    request: Request,
    note_text: str = Form(...),
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """Добавление заметки к лиду"""
    try:
        lead_service = LeadManagementService(session)
        
        success = await lead_service.add_lead_note(
            lead_id=lead_id,
            note_text=note_text,
            added_by=current_user.id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Лид не найден")
        
        # Добавляем сообщение об успехе
        request.session['messages'] = ['Заметка добавлена']
        
        return RedirectResponse(
            url=f"/admin/leads/{lead_id}",
            status_code=302
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при добавлении заметки к лиду {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/export/csv")
async def export_leads_csv(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_async_session),
    status_filter: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Экспорт лидов в CSV"""
    try:
        lead_service = LeadManagementService(session)
        
        # Парсим даты если переданы
        date_from_obj = None
        date_to_obj = None
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты 'от'")
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to)
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты 'до'")
        
        csv_data = await lead_service.export_leads_csv(
            status_filter=status_filter,
            date_from=date_from_obj,
            date_to=date_to_obj
        )
        
        from fastapi.responses import Response
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при экспорте лидов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/stats/dashboard")
async def leads_stats_dashboard(
    request: Request,
    current_user: AdminUser = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_async_session),
    period_days: int = Query(30, ge=1, le=365)
):
    """Статистика лидов для дашборда"""
    try:
        lead_service = LeadManagementService(session)
        
        stats = await lead_service.get_leads_dashboard_stats(period_days)
        
        return {
            "period_days": period_days,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики лидов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")
