"""
Сервис уведомлений менеджерам через Telegram.
Согласно @vision.md - алерты в групповой чат.
"""
import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from src.config.settings import settings
from src.domain.entities.lead import Lead
from src.infrastructure.logging.hybrid_logger import hybrid_logger


class TelegramNotifier:
    """Сервис уведомлений через Telegram"""
    
    def __init__(self, bot: Bot) -> None:
        """
        Инициализация уведомлений.
        
        Args:
            bot: Экземпляр Telegram бота
        """
        self.bot = bot
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def notify_new_lead(self, lead: Lead, chat_id: int) -> bool:
        """
        Уведомление о новом лиде.
        
        Args:
            lead: Объект лида
            chat_id: ID чата пользователя
            
        Returns:
            True если уведомление отправлено успешно
        """
        if not settings.manager_telegram_chat_id:
            await hybrid_logger.warning("MANAGER_TELEGRAM_CHAT_ID не настроен - уведомления отключены")
            return False
        
        try:
            # Формируем сообщение
            message_text = self._format_lead_notification(lead, chat_id)
            
            # Отправляем в групповой чат менеджеров
            await self.bot.send_message(
                chat_id=settings.manager_telegram_chat_id,
                text=message_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            await hybrid_logger.business(
                "Уведомление о лиде отправлено менеджерам",
                {
                    "lead_id": lead.id,
                    "manager_chat_id": settings.manager_telegram_chat_id,
                    "user_chat_id": chat_id
                }
            )
            
            return True
            
        except TelegramAPIError as e:
            await hybrid_logger.error(
                f"Ошибка отправки уведомления в Telegram: {e}",
                {
                    "lead_id": lead.id,
                    "manager_chat_id": settings.manager_telegram_chat_id,
                    "error_code": e.error_code if hasattr(e, 'error_code') else None
                }
            )
            return False
        
        except Exception as e:
            await hybrid_logger.error(f"Неожиданная ошибка при отправке уведомления: {e}")
            return False
    
    async def notify_critical_error(self, error_message: str, context: dict = None) -> bool:
        """
        Уведомление о критической ошибке.
        
        Args:
            error_message: Текст ошибки
            context: Дополнительный контекст
            
        Returns:
            True если уведомление отправлено успешно
        """
        admin_ids = settings.admin_telegram_ids
        if not admin_ids:
            return False
        
        try:
            notification_text = f"🚨 <b>КРИТИЧЕСКАЯ ОШИБКА</b>\n\n"
            notification_text += f"📝 <b>Сообщение:</b> {error_message}\n"
            
            if context:
                notification_text += f"\n📊 <b>Контекст:</b>\n"
                for key, value in context.items():
                    notification_text += f"• {key}: {value}\n"
            
            notification_text += f"\n⏰ Время: {self._get_current_time()}"
            
            # Отправляем всем администраторам
            success_count = 0
            for admin_id in admin_ids:
                try:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=notification_text,
                        parse_mode="HTML"
                    )
                    success_count += 1
                except TelegramAPIError:
                    continue
            
            return success_count > 0
            
        except Exception as e:
            self._logger.error(f"Ошибка отправки критического уведомления: {e}")
            return False
    
    def _format_lead_notification(self, lead: Lead, user_chat_id: int) -> str:
        """Форматирование уведомления о лиде"""
        # Определяем эмодзи по типу
        emoji = "🤖" if lead.auto_created else "📞"
        creation_type = "Автоматически" if lead.auto_created else "Вручную"
        
        message = f"{emoji} <b>Новый лид #{lead.id}</b>\n"
        message += f"📋 <b>Создан:</b> {creation_type}\n\n"
        
        # Основная информация
        message += f"👤 <b>Имя:</b> {lead.get_display_name()}\n"
        
        # Контактные данные
        if lead.phone:
            message += f"📱 <b>Телефон:</b> <code>{lead.phone}</code>\n"
        if lead.email:
            message += f"📧 <b>Email:</b> <code>{lead.email}</code>\n"
        if lead.telegram:
            message += f"💬 <b>Telegram:</b> {lead.telegram}\n"
        if lead.company:
            message += f"🏢 <b>Компания:</b> {lead.company}\n"
        
        # Вопрос/потребность
        if lead.question:
            question_preview = lead.question[:100] + "..." if len(lead.question) > 100 else lead.question
            message += f"\n❓ <b>Вопрос:</b>\n{question_preview}\n"
        
        # Техническая информация
        message += f"\n📊 <b>Источник:</b> {lead.lead_source.value}\n"
        message += f"⏰ <b>Создан:</b> {self._format_datetime_msk(lead.created_at)}"
        
        return message
    
    def _format_datetime(self, dt) -> str:
        """Форматирование даты и времени"""
        if not dt:
            return "—"
        return dt.strftime("%d.%m.%Y %H:%M")

    def _format_datetime_msk(self, dt) -> str:
        """Форматирование даты и времени в московском часовом поясе"""
        if not dt:
            return "—"
        
        from datetime import timezone, timedelta
        
        # Московское время (UTC+3)
        moscow_tz = timezone(timedelta(hours=3))
        
        # Если время в UTC, конвертируем в московское
        if dt.tzinfo is None:
            # Предполагаем что время в UTC
            dt = dt.replace(tzinfo=timezone.utc)
        
        moscow_time = dt.astimezone(moscow_tz)
        return moscow_time.strftime("%d.%m.%Y %H:%M МСК")
    
    def _get_current_time(self) -> str:
        """Получение текущего времени"""
        from datetime import datetime
        return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


# Singleton instance для использования в handlers
_notifier_instance: Optional[TelegramNotifier] = None


def get_telegram_notifier(bot: Bot) -> TelegramNotifier:
    """Получение singleton instance уведомлений"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = TelegramNotifier(bot)
    return _notifier_instance
