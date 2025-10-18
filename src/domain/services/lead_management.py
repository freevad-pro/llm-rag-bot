"""
Сервис для управления лидами в системе.
Реализует бизнес-логику работы с лидами согласно @vision.md
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import csv
import io

from ...infrastructure.database.models import Lead, LeadInteraction


class LeadManagementService:
    """Сервис для управления лидами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_leads_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получение лидов с пагинацией и фильтрацией"""
        
        # Базовый запрос
        query = select(Lead)
        
        # Применяем фильтры
        filters = []
        
        if status_filter:
            filters.append(Lead.status == status_filter)
        
        if search:
            search_filter = or_(
                Lead.name.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
                Lead.company.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Подсчет общего количества
        count_query = select(func.count(Lead.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_count = await self.session.execute(count_query)
        total = total_count.scalar()
        
        # Применяем пагинацию
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Сортировка по дате создания (новые сначала)
        query = query.order_by(Lead.created_at.desc())
        
        # Выполняем запрос
        result = await self.session.execute(query)
        leads = result.scalars().all()
        
        # Вычисляем пагинацию
        total_pages = (total + per_page - 1) // per_page
        
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None
        }
        
        return {
            "leads": leads,
            "pagination": pagination
        }
    
    async def get_lead_by_id(self, lead_id: int) -> Optional[Lead]:
        """Получение лида по ID"""
        query = select(Lead).where(Lead.id == lead_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_lead_interactions(self, lead_id: int) -> List[LeadInteraction]:
        """Получение истории взаимодействий с лидом"""
        query = select(LeadInteraction).where(LeadInteraction.lead_id == lead_id).order_by(LeadInteraction.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_lead_status(
        self,
        lead_id: int,
        new_status: str,
        notes: Optional[str] = None,
        updated_by: int = None
    ) -> bool:
        """Обновление статуса лида"""
        
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return False
        
        # Обновляем статус
        lead.status = new_status
        
        # Добавляем заметку если указана
        if notes:
            interaction = LeadInteraction(
                lead_id=lead_id,
                interaction_type="status_change",
                content=f"Статус изменен на: {new_status}. Заметка: {notes}",
                created_by=updated_by
            )
            self.session.add(interaction)
        
        await self.session.commit()
        return True
    
    async def add_lead_note(
        self,
        lead_id: int,
        note_text: str,
        added_by: int = None
    ) -> bool:
        """Добавление заметки к лиду"""
        
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return False
        
        # Создаем взаимодействие
        interaction = LeadInteraction(
            lead_id=lead_id,
            interaction_type="note",
            content=note_text,
            created_by=added_by
        )
        
        self.session.add(interaction)
        await self.session.commit()
        return True
    
    async def get_leads_stats(self) -> Dict[str, Any]:
        """Получение статистики по лидам"""
        
        # Общее количество лидов
        total_query = select(func.count(Lead.id))
        total_result = await self.session.execute(total_query)
        total_leads = total_result.scalar()
        
        # Количество по статусам
        status_query = select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
        status_result = await self.session.execute(status_query)
        status_counts = dict(status_result.fetchall())
        
        # Лиды за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_query = select(func.count(Lead.id)).where(Lead.created_at >= thirty_days_ago)
        recent_result = await self.session.execute(recent_query)
        recent_leads = recent_result.scalar()
        
        # Лиды за сегодня
        today = datetime.utcnow().date()
        today_query = select(func.count(Lead.id)).where(func.date(Lead.created_at) == today)
        today_result = await self.session.execute(today_query)
        today_leads = today_result.scalar()
        
        return {
            "total": total_leads,
            "by_status": status_counts,
            "recent_30_days": recent_leads,
            "today": today_leads
        }
    
    async def get_leads_dashboard_stats(self, period_days: int = 30) -> Dict[str, Any]:
        """Статистика лидов для дашборда"""
        
        period_start = datetime.utcnow() - timedelta(days=period_days)
        
        # Лиды за период
        period_query = select(func.count(Lead.id)).where(Lead.created_at >= period_start)
        period_result = await self.session.execute(period_query)
        period_leads = period_result.scalar()
        
        # Конверсия по статусам
        conversion_query = select(Lead.status, func.count(Lead.id)).where(Lead.created_at >= period_start).group_by(Lead.status)
        conversion_result = await self.session.execute(conversion_query)
        conversion_data = dict(conversion_result.fetchall())
        
        # Тренд по дням (последние 7 дней)
        trend_days = []
        trend_counts = []
        
        for i in range(7):
            day = datetime.utcnow().date() - timedelta(days=i)
            day_query = select(func.count(Lead.id)).where(func.date(Lead.created_at) == day)
            day_result = await self.session.execute(day_query)
            day_count = day_result.scalar()
            
            trend_days.append(day.strftime("%Y-%m-%d"))
            trend_counts.append(day_count)
        
        return {
            "period_leads": period_leads,
            "conversion_by_status": conversion_data,
            "trend_days": list(reversed(trend_days)),
            "trend_counts": list(reversed(trend_counts))
        }
    
    async def export_leads_csv(
        self,
        status_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> str:
        """Экспорт лидов в CSV"""
        
        # Базовый запрос
        query = select(Lead)
        
        # Применяем фильтры
        filters = []
        
        if status_filter:
            filters.append(Lead.status == status_filter)
        
        if date_from:
            filters.append(Lead.created_at >= date_from)
        
        if date_to:
            filters.append(Lead.created_at <= date_to)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Сортировка
        query = query.order_by(Lead.created_at.desc())
        
        # Выполняем запрос
        result = await self.session.execute(query)
        leads = result.scalars().all()
        
        # Создаем CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        headers = [
            "ID", "Имя", "Email", "Телефон", "Компания", "Вопрос",
            "Статус", "Источник", "Дата создания"
        ]
        writer.writerow(headers)
        
        # Данные
        for lead in leads:
            row = [
                lead.id,
                lead.name or "",
                lead.email or "",
                lead.phone or "",
                lead.company or "",
                lead.question or "",
                lead.status or "",
                lead.lead_source or "",
                lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else ""
            ]
            writer.writerow(row)
        
        return output.getvalue()
