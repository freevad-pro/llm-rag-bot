"""
Сервис для работы с системными логами
"""
from typing import List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Query

from ..entities.system_log import SystemLog, LogLevel
from ...infrastructure.database.models import SystemLog as SystemLogModel
from ...infrastructure.logging.hybrid_logger import hybrid_logger


class SystemLogsService:
    """Сервис для управления системными логами"""

    async def get_logs(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        level_filter: Optional[LogLevel] = None,
        search_query: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        module_filter: Optional[str] = None,
        show_only_errors: bool = False
    ) -> Tuple[List[SystemLog], int]:
        """
        Получить логи с фильтрацией и пагинацией
        Возвращает (логи, общее_количество)
        """
        
        # Базовый запрос
        stmt = select(SystemLogModel)
        count_stmt = select(func.count(SystemLogModel.id))
        
        # Условия фильтрации
        conditions = []
        
        # Фильтр по уровню
        if level_filter:
            conditions.append(SystemLogModel.level == level_filter.value)
        
        # Только ошибки
        if show_only_errors:
            conditions.append(
                SystemLogModel.level.in_([LogLevel.ERROR.value, LogLevel.CRITICAL.value])
            )
        
        # Поиск по тексту
        if search_query and search_query.strip():
            search_pattern = f"%{search_query.strip()}%"
            conditions.append(
                or_(
                    SystemLogModel.message.ilike(search_pattern),
                    SystemLogModel.module.ilike(search_pattern),
                    SystemLogModel.function.ilike(search_pattern)
                )
            )
        
        # Фильтр по модулю
        if module_filter and module_filter.strip():
            conditions.append(SystemLogModel.module.ilike(f"%{module_filter.strip()}%"))
        
        # Фильтр по датам
        if date_from:
            conditions.append(SystemLogModel.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to:
            conditions.append(SystemLogModel.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        # Применяем условия
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        
        # Сортировка: новые сначала
        stmt = stmt.order_by(desc(SystemLogModel.created_at))
        
        # Пагинация
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Выполняем запросы
        logs_result = await session.execute(stmt)
        count_result = await session.execute(count_stmt)
        
        log_models = logs_result.scalars().all()
        total_count = count_result.scalar()
        
        # Конвертируем в domain entities
        logs = [self._model_to_entity(log_model) for log_model in log_models]
        
        return logs, total_count

    async def get_log_by_id(self, session: AsyncSession, log_id: int) -> Optional[SystemLog]:
        """Получить лог по ID"""
        stmt = select(SystemLogModel).where(SystemLogModel.id == log_id)
        result = await session.execute(stmt)
        log_model = result.scalar_one_or_none()
        
        if not log_model:
            return None
        
        return self._model_to_entity(log_model)

    async def get_log_statistics(self, session: AsyncSession, days: int = 7) -> dict:
        """
        Получить статистику логов за последние дни
        """
        from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from_date = from_date.replace(day=from_date.day - days + 1)
        
        # Общая статистика
        total_stmt = select(func.count(SystemLogModel.id)).where(
            SystemLogModel.created_at >= from_date
        )
        
        # По уровням
        stats_by_level = {}
        for level in LogLevel:
            level_stmt = select(func.count(SystemLogModel.id)).where(
                and_(
                    SystemLogModel.created_at >= from_date,
                    SystemLogModel.level == level.value
                )
            )
            result = await session.execute(level_stmt)
            stats_by_level[level.value] = result.scalar()
        
        # Общее количество
        total_result = await session.execute(total_stmt)
        total_logs = total_result.scalar()
        
        # Топ модулей с ошибками
        error_modules_stmt = select(
            SystemLogModel.module,
            func.count(SystemLogModel.id).label('error_count')
        ).where(
            and_(
                SystemLogModel.created_at >= from_date,
                SystemLogModel.level.in_([LogLevel.ERROR.value, LogLevel.CRITICAL.value])
            )
        ).group_by(SystemLogModel.module).order_by(desc('error_count')).limit(5)
        
        error_modules_result = await session.execute(error_modules_stmt)
        error_modules = [
            {"module": row.module, "count": row.error_count}
            for row in error_modules_result
        ]
        
        return {
            "total_logs": total_logs,
            "by_level": stats_by_level,
            "error_modules": error_modules,
            "period_days": days
        }

    async def get_available_modules(self, session: AsyncSession) -> List[str]:
        """Получить список доступных модулей для фильтрации"""
        stmt = select(SystemLogModel.module).distinct().order_by(SystemLogModel.module)
        result = await session.execute(stmt)
        return [row[0] for row in result.fetchall() if row[0]]

    async def delete_old_logs(self, session: AsyncSession, days_to_keep: int = 30) -> int:
        """
        Удалить старые логи (старше указанного количества дней)
        Возвращает количество удаленных записей
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Считаем количество для удаления
        count_stmt = select(func.count(SystemLogModel.id)).where(
            SystemLogModel.created_at < cutoff_date
        )
        count_result = await session.execute(count_stmt)
        count_to_delete = count_result.scalar()
        
        if count_to_delete > 0:
            # Удаляем старые логи
            from sqlalchemy import delete
            delete_stmt = delete(SystemLogModel).where(
                SystemLogModel.created_at < cutoff_date
            )
            await session.execute(delete_stmt)
            await session.commit()
            
            await hybrid_logger.info(f"Удалено {count_to_delete} старых логов (старше {days_to_keep} дней)")
        
        return count_to_delete

    def _model_to_entity(self, log_model: SystemLogModel) -> SystemLog:
        """Конвертировать модель БД в domain entity"""
        try:
            level = LogLevel(log_model.level)
        except ValueError:
            level = LogLevel.INFO  # Fallback для неизвестных уровней
        
        return SystemLog(
            id=log_model.id,
            level=level,
            message=log_model.message,
            module=log_model.module or "unknown",
            function=log_model.function or "unknown",
            line_number=log_model.line_number or 0,
            timestamp=log_model.created_at,
            extra_data=log_model.extra_data
        )


# Singleton instance
system_logs_service = SystemLogsService()
