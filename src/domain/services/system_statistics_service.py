"""
Сервис для получения статистики системы
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from ...infrastructure.database.models import User, Conversation, Lead, AdminUser, CatalogVersion
from ...infrastructure.search.catalog_service import CatalogSearchService


class SystemStatisticsService:
    """Сервис для получения статистики системы"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.catalog_service = CatalogSearchService()
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Получить статистику для панели управления"""
        try:
            # Получаем статистику параллельно
            users_count = await self._get_users_count()
            conversations_count = await self._get_conversations_count()
            leads_count = await self._get_leads_count()
            catalog_products_count = await self._get_catalog_products_count()
            
            return {
                "users_count": users_count,
                "conversations_count": conversations_count,
                "leads_count": leads_count,
                "catalog_products": catalog_products_count
            }
            
        except Exception as e:
            # В случае ошибки возвращаем нули
            return {
                "users_count": 0,
                "conversations_count": 0,
                "leads_count": 0,
                "catalog_products": 0
            }
    
    async def _get_users_count(self) -> int:
        """Получить количество пользователей"""
        try:
            result = await self.session.execute(
                select(func.count(User.id))
            )
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_conversations_count(self) -> int:
        """Получить количество диалогов"""
        try:
            result = await self.session.execute(
                select(func.count(Conversation.id))
            )
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_leads_count(self) -> int:
        """Получить количество лидов"""
        try:
            result = await self.session.execute(
                select(func.count(Lead.id))
            )
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_catalog_products_count(self) -> int:
        """Получить количество товаров в каталоге"""
        try:
            # Сначала пытаемся получить из активной версии каталога
            result = await self.session.execute(
                select(CatalogVersion.products_count)
                .where(CatalogVersion.is_active == True)
                .order_by(CatalogVersion.created_at.desc())
                .limit(1)
            )
            products_count = result.scalar()
            
            if products_count is not None:
                return products_count
            
            # Если в БД нет информации, пытаемся получить из Chroma
            try:
                collection = await self.catalog_service._get_collection()
                if collection:
                    # Получаем все документы для подсчета
                    results = collection.get(include=["metadatas"])
                    if results and results["ids"]:
                        return len(results["ids"])
            except Exception:
                pass
            
            return 0
            
        except Exception:
            return 0
    
    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Получить детальную статистику"""
        try:
            # Основная статистика
            dashboard_stats = await self.get_dashboard_stats()
            
            # Дополнительная статистика
            today_leads = await self._get_today_leads_count()
            recent_leads = await self._get_recent_leads_count(days=30)
            active_conversations = await self._get_active_conversations_count()
            admin_users_count = await self._get_admin_users_count()
            
            return {
                **dashboard_stats,
                "today_leads": today_leads,
                "recent_leads_30_days": recent_leads,
                "active_conversations": active_conversations,
                "admin_users_count": admin_users_count
            }
            
        except Exception as e:
            return dashboard_stats
    
    async def _get_today_leads_count(self) -> int:
        """Получить количество лидов за сегодня"""
        try:
            today = datetime.utcnow().date()
            result = await self.session.execute(
                select(func.count(Lead.id))
                .where(func.date(Lead.created_at) == today)
            )
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_recent_leads_count(self, days: int = 30) -> int:
        """Получить количество лидов за последние N дней"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            result = await self.session.execute(
                select(func.count(Lead.id))
                .where(Lead.created_at >= since_date)
            )
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_active_conversations_count(self) -> int:
        """Получить количество активных диалогов"""
        try:
            result = await self.session.execute(
                select(func.count(Conversation.id))
                .where(Conversation.status == "active")
            )
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_admin_users_count(self) -> int:
        """Получить количество администраторов"""
        try:
            result = await self.session.execute(
                select(func.count(AdminUser.id))
                .where(AdminUser.is_active == True)
            )
            return result.scalar() or 0
        except Exception:
            return 0
