"""
Сервис для отправки алертов о превышении лимитов AI расходов
"""
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.settings import get_settings
from .usage_statistics_service import usage_statistics_service
from ...infrastructure.logging.hybrid_logger import hybrid_logger

logger = logging.getLogger(__name__)


class CostAlertService:
    """Сервис для мониторинга расходов и отправки алертов"""
    
    def __init__(self):
        self.settings = get_settings()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def check_and_send_alerts(self, session: AsyncSession) -> bool:
        """
        Проверяет текущие расходы и отправляет алерты при необходимости.
        Возвращает True если все в порядке, False если превышены лимиты.
        """
        if not self.settings.cost_alert_enabled:
            return True
        
        try:
            # Получаем статистику за текущий месяц
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            summary = await usage_statistics_service.get_monthly_summary(
                session, current_year, current_month
            )
            
            # Проверяем лимит токенов
            token_usage_percent = summary.total_tokens / self.settings.monthly_token_limit
            
            # Проверяем лимит расходов (если есть цены)
            cost_usage_percent = 0.0
            if hasattr(summary, 'total_cost_usd') and summary.total_cost_usd and summary.total_cost_usd > 0:
                cost_usage_percent = summary.total_cost_usd / self.settings.monthly_cost_limit_usd
            
            # Определяем максимальный процент использования
            max_usage_percent = max(token_usage_percent, cost_usage_percent)
            
            # Проверяем пороги
            if max_usage_percent >= 1.0:
                # Превышен лимит - критический алерт
                await self._send_limit_exceeded_alert(summary, token_usage_percent, cost_usage_percent)
                return False
                
            elif max_usage_percent >= self.settings.cost_alert_threshold:
                # Приближение к лимиту - предупреждение
                await self._send_threshold_alert(summary, token_usage_percent, cost_usage_percent)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Ошибка при проверке лимитов: {e}")
            await hybrid_logger.error(
                f"Ошибка при проверке лимитов AI расходов: {e}",
                metadata={"error": str(e), "service": "CostAlertService"}
            )
            return True  # В случае ошибки не блокируем работу
    
    async def _send_threshold_alert(
        self, 
        summary, 
        token_percent: float, 
        cost_percent: float
    ) -> None:
        """Отправляет предупреждение о приближении к лимиту"""
        
        threshold_percent = int(self.settings.cost_alert_threshold * 100)
        
        message = f"⚠️ **Предупреждение о расходах на AI**\n\n"
        message += f"📅 **Месяц:** {summary.year}-{summary.month:02d}\n"
        message += f"🎯 **Порог алерта:** {threshold_percent}%\n\n"
        
        if token_percent >= self.settings.cost_alert_threshold:
            token_used = f"{summary.total_tokens:,}"
            token_limit = f"{self.settings.monthly_token_limit:,}"
            message += f"🔢 **Токены:** {token_used} / {token_limit} ({token_percent:.1%})\n"
        
        if cost_percent >= self.settings.cost_alert_threshold and hasattr(summary, 'total_cost_usd') and summary.total_cost_usd:
            message += f"💰 **Расходы:** ${summary.total_cost_usd:.2f} / ${self.settings.monthly_cost_limit_usd:.2f} ({cost_percent:.1%})\n"
        
        message += f"\n📊 **Детали по провайдерам:**\n"
        for provider, tokens in summary.providers.items():
            message += f"• {provider.upper()}: {tokens:,} токенов\n"
        
        message += f"\n📊 **Детали по моделям:**\n"
        for model, tokens in summary.models.items():
            message += f"• {model}: {tokens:,} токенов\n"
        
        await self._send_to_admins(message)
    
    async def _send_limit_exceeded_alert(
        self, 
        summary, 
        token_percent: float, 
        cost_percent: float
    ) -> None:
        """Отправляет критический алерт о превышении лимита"""
        
        message = f"🚨 **КРИТИЧНО: Превышен лимит AI расходов!**\n\n"
        message += f"📅 **Месяц:** {summary.year}-{summary.month:02d}\n"
        
        if token_percent >= 1.0:
            token_used = f"{summary.total_tokens:,}"
            token_limit = f"{self.settings.monthly_token_limit:,}"
            message += f"🔢 **Токены:** {token_used} / {token_limit} ({token_percent:.1%}) ❌\n"
        
        if cost_percent >= 1.0 and hasattr(summary, 'total_cost_usd') and summary.total_cost_usd:
            message += f"💰 **Расходы:** ${summary.total_cost_usd:.2f} / ${self.settings.monthly_cost_limit_usd:.2f} ({cost_percent:.1%}) ❌\n"
        
        if self.settings.auto_disable_on_limit:
            message += f"\n⛔ **Автоотключение активно** - бот будет заблокирован!\n"
        
        message += f"\n📊 **Детали по провайдерам:**\n"
        for provider, tokens in summary.providers.items():
            message += f"• {provider.upper()}: {tokens:,} токенов\n"
        
        message += f"\n📊 **Детали по моделям:**\n"
        for model, tokens in summary.models.items():
            message += f"• {model}: {tokens:,} токенов\n"
        
        message += f"\n🔧 **Действия:**\n"
        message += f"• Проверьте настройки в админ-панели\n"
        message += f"• Увеличьте лимиты или отключите автоблокировку\n"
        
        await self._send_to_admins(message)
    
    async def send_weekly_report(self, session: AsyncSession) -> None:
        """Отправляет еженедельный отчет об использовании"""
        
        if not self.settings.weekly_usage_report:
            return
        
        try:
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            summary = await usage_statistics_service.get_monthly_summary(
                session, current_year, current_month
            )
            
            token_percent = summary.total_tokens / self.settings.monthly_token_limit
            cost_percent = 0.0
            if hasattr(summary, 'total_cost_usd') and summary.total_cost_usd and summary.total_cost_usd > 0:
                cost_percent = summary.total_cost_usd / self.settings.monthly_cost_limit_usd
            
            message = f"📊 **Еженедельный отчет AI использования**\n\n"
            message += f"📅 **Месяц:** {summary.year}-{summary.month:02d}\n"
            message += f"🔢 **Токены:** {summary.total_tokens:,} / {self.settings.monthly_token_limit:,} ({token_percent:.1%})\n"
            
            if hasattr(summary, 'total_cost_usd') and summary.total_cost_usd and summary.total_cost_usd > 0:
                message += f"💰 **Расходы:** ${summary.total_cost_usd:.2f} / ${self.settings.monthly_cost_limit_usd:.2f} ({cost_percent:.1%})\n"
            
            message += f"\n📈 **Использование по провайдерам:**\n"
            for provider, tokens in summary.providers.items():
                message += f"• **{provider.upper()}:** {tokens:,} токенов\n"
            
            message += f"\n📈 **Использование по моделям:**\n"
            for model, tokens in summary.models.items():
                model_percent = (tokens / summary.total_tokens) * 100 if summary.total_tokens > 0 else 0
                message += f"• **{model}:** {tokens:,} ({model_percent:.1f}%)\n"
            
            await self._send_to_admins(message)
            
        except Exception as e:
            self._logger.error(f"Ошибка при отправке еженедельного отчета: {e}")
    
    async def _send_to_admins(self, message: str) -> None:
        """Отправляет сообщение всем администраторам"""
        
        admin_ids = self.settings.admin_telegram_ids_list
        if not admin_ids:
            self._logger.warning("Нет настроенных Telegram ID администраторов для алертов")
            return
        
        if not self.settings.bot_token:
            self._logger.warning("Не настроен BOT_TOKEN для отправки алертов")
            return
        
        try:
            # Используем контекстный менеджер для правильного управления ресурсами
            from src.infrastructure.utils.bot_utils import get_bot_for_notifications
            
            async with get_bot_for_notifications() as bot:
                for admin_id in admin_ids:
                    try:
                        await bot.send_message(
                            chat_id=admin_id, 
                            text=message,
                            parse_mode="Markdown"
                        )
                        self._logger.info(f"Алерт отправлен администратору {admin_id}")
                    except Exception as e:
                        self._logger.error(f"Ошибка отправки алерта администратору {admin_id}: {e}")
                    
        except Exception as e:
            self._logger.error(f"Ошибка инициализации бота для алертов: {e}")
    
    def should_block_ai_requests(self, session: AsyncSession) -> bool:
        """
        Проверяет, нужно ли блокировать AI запросы из-за превышения лимитов.
        Синхронная версия для быстрой проверки в middleware.
        """
        if not self.settings.auto_disable_on_limit:
            return False
        
        # TODO: Реализовать кэширование результата проверки лимитов
        # Пока возвращаем False, чтобы не блокировать работу
        return False


# Глобальный экземпляр сервиса
cost_alert_service = CostAlertService()
