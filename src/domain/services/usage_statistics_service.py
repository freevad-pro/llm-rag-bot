"""
Сервис для работы со статистикой использования AI токенов
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.dialects.postgresql import insert

from ...infrastructure.database.models import UsageStatistics as UsageStatisticsModel
from ...infrastructure.logging.hybrid_logger import hybrid_logger
from ..entities.usage_statistics import (
    UsageStatistics, UsageStatisticsCreate, UsageStatisticsUpdate,
    MonthlyUsageSummary, UsageLimits
)


class UsageStatisticsService:
    """Сервис для управления статистикой использования AI"""
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def add_tokens_usage(
        self,
        session: AsyncSession,
        provider: str,
        model: str,
        tokens_used: int,
        current_date: Optional[datetime] = None
    ) -> bool:
        """
        Добавляет использованные токены к статистике текущего месяца.
        Создает запись если её нет.
        
        Args:
            session: Сессия БД
            provider: Провайдер AI (openai, yandexgpt)
            model: Модель AI (gpt-4o-mini, gpt-4o, etc.)
            tokens_used: Количество использованных токенов
            current_date: Дата (по умолчанию текущая)
            
        Returns:
            True если успешно обновлено
        """
        try:
            if current_date is None:
                current_date = datetime.now()
            
            year = current_date.year
            month = current_date.month
            
            # Используем UPSERT для атомарного обновления
            stmt = insert(UsageStatisticsModel).values(
                provider=provider,
                model=model,
                year=year,
                month=month,
                total_tokens=tokens_used,
                currency='USD' if provider == 'openai' else 'RUB'
            )
            
            # При конфликте - увеличиваем total_tokens
            stmt = stmt.on_conflict_do_update(
                index_elements=['provider', 'model', 'year', 'month'],
                set_={
                    'total_tokens': UsageStatisticsModel.total_tokens + stmt.excluded.total_tokens,
                    'updated_at': func.now()
                }
            )
            
            await session.execute(stmt)
            await session.commit()
            
            self._logger.debug(f"Добавлено {tokens_used} токенов для {provider}/{model}")
            
            # Проверяем лимиты после добавления токенов
            await self._check_limits_after_usage(session)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Ошибка добавления токенов: {e}")
            await session.rollback()
            return False
    
    async def get_monthly_summary(
        self,
        session: AsyncSession,
        year: int,
        month: int
    ) -> MonthlyUsageSummary:
        """Получает сводку использования за месяц"""
        try:
            query = select(UsageStatisticsModel).where(
                and_(
                    UsageStatisticsModel.year == year,
                    UsageStatisticsModel.month == month
                )
            )
            
            result = await session.execute(query)
            records = result.scalars().all()
            
            total_tokens = sum(r.total_tokens for r in records)
            providers = {}
            models = {}
            
            for record in records:
                providers[record.provider] = providers.get(record.provider, 0) + record.total_tokens
                models[record.model] = models.get(record.model, 0) + record.total_tokens
            
            return MonthlyUsageSummary(
                year=year,
                month=month,
                total_tokens=total_tokens,
                providers=providers,
                models=models
            )
            
        except Exception as e:
            self._logger.error(f"Ошибка получения сводки: {e}")
            return MonthlyUsageSummary(
                year=year,
                month=month,
                total_tokens=0,
                providers={},
                models={}
            )
    
    async def get_current_month_usage(self, session: AsyncSession) -> MonthlyUsageSummary:
        """Получает использование за текущий месяц"""
        now = datetime.now()
        return await self.get_monthly_summary(session, now.year, now.month)
    
    async def update_pricing(
        self,
        session: AsyncSession,
        provider: str,
        model: str,
        year: int,
        month: int,
        price_per_1k_tokens: str,
        currency: str = "USD"
    ) -> bool:
        """Обновляет цены для конкретной записи"""
        try:
            query = select(UsageStatisticsModel).where(
                and_(
                    UsageStatisticsModel.provider == provider,
                    UsageStatisticsModel.model == model,
                    UsageStatisticsModel.year == year,
                    UsageStatisticsModel.month == month
                )
            )
            
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            
            if record:
                record.price_per_1k_tokens = price_per_1k_tokens
                record.currency = currency
                record.updated_at = datetime.now()
                
                await session.commit()
                
                await hybrid_logger.business(
                    f"Обновлена цена для {provider}/{model} {year}-{month:02d}: {price_per_1k_tokens} {currency}",
                    metadata={
                        "provider": provider,
                        "model": model,
                        "year": year,
                        "month": month,
                        "price": price_per_1k_tokens,
                        "currency": currency
                    }
                )
                
                return True
            else:
                self._logger.warning(f"Запись не найдена: {provider}/{model} {year}-{month}")
                return False
                
        except Exception as e:
            self._logger.error(f"Ошибка обновления цены: {e}")
            await session.rollback()
            return False
    
    async def update_price_per_1k_tokens(
        self,
        session: AsyncSession,
        stat_id: int,
        price_per_1k_tokens: str,
        currency: str
    ) -> bool:
        """Обновляет цену за 1K токенов для записи по ID"""
        try:
            query = select(UsageStatisticsModel).where(UsageStatisticsModel.id == stat_id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            
            if record:
                record.price_per_1k_tokens = price_per_1k_tokens
                record.currency = currency
                record.updated_at = datetime.now()
                
                await session.commit()
                
                await hybrid_logger.business(
                    f"Обновлена цена для записи ID {stat_id}: {price_per_1k_tokens} {currency}",
                    metadata={
                        "stat_id": stat_id,
                        "provider": record.provider,
                        "model": record.model,
                        "year": record.year,
                        "month": record.month,
                        "price": price_per_1k_tokens,
                        "currency": currency
                    }
                )
                
                return True
            else:
                self._logger.warning(f"Запись с ID {stat_id} не найдена")
                return False
                
        except Exception as e:
            self._logger.error(f"Ошибка обновления цены по ID: {e}")
            await session.rollback()
            return False
    
    async def get_all_statistics(
        self,
        session: AsyncSession,
        limit: int = 12
    ) -> List[UsageStatistics]:
        """Получает все записи статистики (последние N месяцев)"""
        try:
            query = select(UsageStatisticsModel).order_by(
                UsageStatisticsModel.year.desc(),
                UsageStatisticsModel.month.desc(),
                UsageStatisticsModel.provider,
                UsageStatisticsModel.model
            ).limit(limit * 10)  # Примерно limit месяцев
            
            result = await session.execute(query)
            records = result.scalars().all()
            
            return [
                UsageStatistics(
                    id=r.id,
                    provider=r.provider,
                    model=r.model,
                    year=r.year,
                    month=r.month,
                    total_tokens=r.total_tokens,
                    price_per_1k_tokens=r.price_per_1k_tokens,
                    currency=r.currency,
                    created_at=r.created_at,
                    updated_at=r.updated_at
                )
                for r in records
            ]
            
        except Exception as e:
            self._logger.error(f"Ошибка получения статистики: {e}")
            return []
    
    async def check_usage_limits(
        self,
        session: AsyncSession,
        limits: UsageLimits
    ) -> Dict[str, Any]:
        """
        Проверяет превышение лимитов использования
        
        Returns:
            Dict с информацией о лимитах и превышениях
        """
        try:
            current_usage = await self.get_current_month_usage(session)
            
            # Проверка лимита токенов
            token_usage_percent = (current_usage.total_tokens / limits.monthly_token_limit) if limits.monthly_token_limit > 0 else 0
            token_limit_exceeded = current_usage.total_tokens >= limits.monthly_token_limit
            token_alert_needed = token_usage_percent >= limits.cost_alert_threshold
            
            return {
                "current_tokens": current_usage.total_tokens,
                "token_limit": limits.monthly_token_limit,
                "token_usage_percent": round(token_usage_percent * 100, 1),
                "token_limit_exceeded": token_limit_exceeded,
                "token_alert_needed": token_alert_needed,
                "should_disable": token_limit_exceeded and limits.auto_disable_on_limit,
                "usage_summary": current_usage
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка проверки лимитов: {e}")
            return {
                "current_tokens": 0,
                "token_limit": limits.monthly_token_limit,
                "token_usage_percent": 0,
                "token_limit_exceeded": False,
                "token_alert_needed": False,
                "should_disable": False,
                "usage_summary": None
            }


    async def _check_limits_after_usage(self, session: AsyncSession) -> None:
        """
        Проверяет лимиты после добавления токенов и отправляет алерты при необходимости.
        Выполняется асинхронно, чтобы не блокировать основной поток.
        """
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from .cost_alert_service import cost_alert_service
            
            # Проверяем лимиты в фоновом режиме
            await cost_alert_service.check_and_send_alerts(session)
            
        except Exception as e:
            # Логируем ошибку, но не прерываем основной процесс
            self._logger.error(f"Ошибка при проверке лимитов: {e}")


# Глобальный экземпляр сервиса
usage_statistics_service = UsageStatisticsService()
