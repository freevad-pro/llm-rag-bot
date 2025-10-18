"""
API роуты для управления статистикой использования AI
"""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.database.connection import get_session
from ....domain.services.usage_statistics_service import usage_statistics_service
from ....domain.entities.admin_user import AdminUser
from .admin import get_current_admin_user, require_admin_user
from fastapi.templating import Jinja2Templates
from ....infrastructure.logging.hybrid_logger import hybrid_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/usage-statistics", tags=["usage_statistics"])

# Настройка шаблонов
templates = Jinja2Templates(directory="src/presentation/templates")


@router.get("/", response_class=HTMLResponse)
async def usage_statistics_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Страница управления статистикой использования AI
    """
    try:
        # Получаем статистику за последние 12 месяцев
        all_stats = await usage_statistics_service.get_all_statistics(session, limit=120)
        
        # Проверяем, есть ли данные
        if not all_stats:
            # Если данных нет, возвращаем пустую статистику
            return templates.TemplateResponse(
                "admin/usage_statistics.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "page_title": "Статистика использования AI",
                    "monthly_stats": [],
                    "current_month": f"{datetime.now().year}-{datetime.now().month:02d}"
                }
            )
        
        # Группируем по месяцам
        monthly_stats = {}
        for stat in all_stats:
            month_key = f"{stat.year}-{stat.month:02d}"
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'year': stat.year,
                    'month': stat.month,
                    'total_tokens': 0,
                    'total_cost_usd': 0.0,
                    'records': []
                }
            
            monthly_stats[month_key]['total_tokens'] += stat.total_tokens
            monthly_stats[month_key]['records'].append(stat)
            
            # Рассчитываем стоимость если есть цена
            if stat.price_per_1k_tokens:
                try:
                    price = float(stat.price_per_1k_tokens)
                    tokens_k = stat.total_tokens / 1000
                    cost = tokens_k * price
                    
                    if stat.currency == 'USD':
                        monthly_stats[month_key]['total_cost_usd'] += cost
                    elif stat.currency == 'RUB':
                        # Примерный курс: 1 USD = 95 RUB
                        monthly_stats[month_key]['total_cost_usd'] += cost / 95
                except (ValueError, TypeError):
                    pass
        
        # Сортируем по месяцам (новые сначала)
        sorted_months = sorted(monthly_stats.items(), key=lambda x: (x[1]['year'], x[1]['month']), reverse=True)
        
        return templates.TemplateResponse(
            "admin/usage_statistics.html",
            {
                "request": request,
                "current_user": current_user,
                "page_title": "Статистика использования AI",
                "monthly_stats": sorted_months,
                "current_month": f"{datetime.now().year}-{datetime.now().month:02d}"
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке статистики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при загрузке статистики")


@router.post("/update-price/{stat_id}")
async def update_price(
    stat_id: int,
    price: str = Form(...),
    currency: str = Form(...),
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Обновление цены за 1K токенов для конкретной записи статистики
    """
    try:
        # Валидируем цену
        try:
            float(price)
        except ValueError:
            return {"success": False, "error": "Некорректная цена"}
        
        if currency not in ['USD', 'RUB']:
            return {"success": False, "error": "Поддерживаются только USD и RUB"}
        
        # Обновляем цену
        success = await usage_statistics_service.update_price_per_1k_tokens(
            session, stat_id, price, currency
        )
        
        if success:
            await hybrid_logger.business(
                f"Обновлена цена для статистики ID {stat_id}: {price} {currency}",
                metadata={
                    "admin_id": current_user.id,
                    "stat_id": stat_id,
                    "price": price,
                    "currency": currency
                }
            )
            return {"success": True, "message": "Цена обновлена"}
        else:
            return {"success": False, "error": "Ошибка при обновлении цены"}
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении цены: {e}")
        return {"success": False, "error": "Внутренняя ошибка сервера"}


@router.get("/monthly-summary/{year}/{month}")
async def get_monthly_summary(
    year: int,
    month: int,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Получение детальной сводки за конкретный месяц
    """
    try:
        summary = await usage_statistics_service.get_monthly_summary(session, year, month)
        
        return {
            "success": True,
            "summary": {
                "year": summary.year,
                "month": summary.month,
                "total_tokens": summary.total_tokens,
                "total_cost_usd": float(summary.total_cost_usd) if summary.total_cost_usd else 0.0,
                "providers": summary.providers,
                "models": summary.models
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении сводки: {e}")
        return {"success": False, "error": "Ошибка при получении сводки"}
