"""
Фоновая задача для мониторинга неактивных пользователей.
Согласно @vision.md - автоматическое создание лидов при неактивности.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import async_session_factory
from src.application.telegram.services.lead_service import LeadService
from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.infrastructure.notifications.telegram_notifier import TelegramNotifier


class InactiveUsersMonitor:
    """Монитор неактивных пользователей для автосоздания лидов"""
    
    def __init__(
        self, 
        lead_service: LeadService,
        notifier: TelegramNotifier,
        check_interval_minutes: int = 10,
        inactivity_threshold_minutes: int = 120  # 2 часа вместо 30 минут
    ) -> None:
        """
        Инициализация монитора.
        
        Args:
            lead_service: Сервис управления лидами
            notifier: Сервис уведомлений
            check_interval_minutes: Интервал проверки (минуты)
            inactivity_threshold_minutes: Порог неактивности (минуты)
        """
        self.lead_service = lead_service
        self.notifier = notifier
        self.check_interval = check_interval_minutes * 60  # в секундах
        self.inactivity_threshold = inactivity_threshold_minutes
        self._running = False
        self._task: asyncio.Task = None
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def start(self) -> None:
        """Запуск мониторинга"""
        if self._running:
            await hybrid_logger.warning("Монитор неактивных пользователей уже запущен")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        
        await hybrid_logger.info(
            f"Запущен монитор неактивных пользователей "
            f"(проверка каждые {self.check_interval//60} мин, "
            f"порог неактивности {self.inactivity_threshold} мин)"
        )
    
    async def stop(self) -> None:
        """Остановка мониторинга"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await hybrid_logger.info("Монитор неактивных пользователей остановлен")
    
    async def _monitor_loop(self) -> None:
        """Основной цикл мониторинга"""
        while self._running:
            try:
                await self._check_inactive_users()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await hybrid_logger.error(f"Ошибка в цикле мониторинга: {e}")
                # Продолжаем работу после ошибки
                await asyncio.sleep(self.check_interval)
    
    async def _check_inactive_users(self) -> None:
        """Проверка неактивных пользователей"""
        try:
            async with async_session_factory() as session:
                inactive_users = await self.lead_service.find_inactive_users(
                    session, 
                    self.inactivity_threshold
                )
                
                if not inactive_users:
                    self._logger.debug("Неактивных пользователей не найдено")
                    return
                
                await hybrid_logger.info(f"Найдено {len(inactive_users)} неактивных пользователей")
                
                # Обрабатываем каждого пользователя
                created_leads = 0
                for user_id, last_activity in inactive_users:
                    try:
                        lead = await self.lead_service.auto_create_lead_for_user(
                            session, 
                            user_id
                        )
                        
                        if lead:
                            created_leads += 1
                            
                            # Уведомляем менеджеров
                            await self.notifier.notify_new_lead(lead, user_id)
                            
                            await hybrid_logger.business(
                                "Автоматически создан лид для неактивного пользователя",
                                {
                                    "user_id": user_id,
                                    "lead_id": lead.id,
                                    "last_activity": last_activity.isoformat() if last_activity else None,
                                    "inactivity_minutes": self.inactivity_threshold
                                }
                            )
                        
                    except Exception as e:
                        await hybrid_logger.error(
                            f"Ошибка создания лида для пользователя {user_id}: {e}"
                        )
                        continue
                
                if created_leads > 0:
                    await hybrid_logger.business(
                        f"Автоматически создано {created_leads} лидов для неактивных пользователей"
                    )
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка проверки неактивных пользователей: {e}")
    
    def is_running(self) -> bool:
        """Проверка состояния мониторинга"""
        return self._running and self._task and not self._task.done()


# Singleton instance
_monitor_instance: InactiveUsersMonitor = None


def get_inactive_users_monitor(
    lead_service: LeadService, 
    notifier: TelegramNotifier
) -> InactiveUsersMonitor:
    """Получение singleton instance монитора"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = InactiveUsersMonitor(lead_service, notifier)
    return _monitor_instance
