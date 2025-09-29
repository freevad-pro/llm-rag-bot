"""
Тесты для TelegramNotifier
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram.exceptions import TelegramAPIError

from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
from src.domain.entities.lead import Lead, LeadSource


class TestTelegramNotifier:
    """Тесты для TelegramNotifier"""
    
    @pytest.fixture
    def mock_bot(self):
        """Мок Telegram бота"""
        bot = Mock()
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def notifier(self, mock_bot):
        """Экземпляр TelegramNotifier"""
        return TelegramNotifier(mock_bot)
    
    @pytest.fixture
    def sample_lead(self):
        """Тестовый лид"""
        return Lead(
            id=1,
            first_name="Иван",
            last_name="Петров",
            phone="+79001234567",
            email="ivan@example.com",
            telegram="@ivan_petrov",
            company="ООО Тест",
            question="Нужна консультация по товарам",
            lead_source=LeadSource.TELEGRAM,
            auto_created=True
        )
    
    @pytest.mark.asyncio
    async def test_notify_critical_error_multiple_admins_success(self, notifier, mock_bot):
        """Тест успешной отправки критического уведомления нескольким админам"""
        # Подготовка
        admin_ids = [123456789, 987654321, 555666777]
        
        with patch('src.infrastructure.notifications.telegram_notifier.settings') as mock_settings:
            mock_settings.admin_telegram_ids_list = admin_ids
            
            with patch('src.infrastructure.notifications.telegram_notifier.hybrid_logger') as mock_logger:
                mock_logger.info = AsyncMock()
                mock_logger.business = AsyncMock()
                mock_logger.error = AsyncMock()
                
                # Выполнение
                result = await notifier.notify_critical_error(
                    "Тестовая критическая ошибка",
                    {"component": "test", "severity": "high"}
                )
        
        # Проверки
        assert result is True
        assert mock_bot.send_message.call_count == 3
        
        # Проверяем что отправлено каждому админу
        sent_to_ids = [call.kwargs['chat_id'] for call in mock_bot.send_message.call_args_list]
        assert set(sent_to_ids) == set(admin_ids)
        
        # Проверяем содержимое сообщения
        message_text = mock_bot.send_message.call_args_list[0].kwargs['text']
        assert "🚨 КРИТИЧЕСКАЯ ОШИБКА" in message_text
        assert "Тестовая критическая ошибка" in message_text
        assert "component: test" in message_text
        assert "severity: high" in message_text
        
        # Проверяем логирование
        assert mock_logger.info.call_count == 3  # По одному для каждого админа
        assert mock_logger.business.call_count == 1  # Общий успех
    
    @pytest.mark.asyncio
    async def test_notify_critical_error_partial_failure(self, notifier, mock_bot):
        """Тест частичной неудачи при отправке критического уведомления"""
        # Подготовка
        admin_ids = [123456789, 987654321, 555666777]
        
        # Настраиваем мок - второй админ недоступен
        async def mock_send_message(chat_id, **kwargs):
            if chat_id == 987654321:
                raise TelegramAPIError("Пользователь заблокировал бота")
        
        mock_bot.send_message = AsyncMock(side_effect=mock_send_message)
        
        with patch('src.infrastructure.notifications.telegram_notifier.settings') as mock_settings:
            mock_settings.admin_telegram_ids_list = admin_ids
            
            with patch('src.infrastructure.notifications.telegram_notifier.hybrid_logger') as mock_logger:
                mock_logger.info = AsyncMock()
                mock_logger.business = AsyncMock()
                mock_logger.error = AsyncMock()
                mock_logger.warning = AsyncMock()
                
                # Выполнение
                result = await notifier.notify_critical_error("Тестовая ошибка")
        
        # Проверки
        assert result is True  # Хотя бы одному админу доставлено
        assert mock_bot.send_message.call_count == 3
        
        # Проверяем логирование
        assert mock_logger.info.call_count == 2  # Успешные отправки
        assert mock_logger.error.call_count == 1  # Ошибка отправки
        assert mock_logger.business.call_count == 1  # Общий результат (2/3)
    
    @pytest.mark.asyncio
    async def test_notify_critical_error_all_failures(self, notifier, mock_bot):
        """Тест полной неудачи при отправке критического уведомления"""
        # Подготовка
        admin_ids = [123456789, 987654321]
        
        # Все отправки неудачны
        mock_bot.send_message = AsyncMock(side_effect=TelegramAPIError("Сервис недоступен"))
        
        with patch('src.infrastructure.notifications.telegram_notifier.settings') as mock_settings:
            mock_settings.admin_telegram_ids_list = admin_ids
            
            with patch('src.infrastructure.notifications.telegram_notifier.hybrid_logger') as mock_logger:
                mock_logger.info = AsyncMock()
                mock_logger.business = AsyncMock()
                mock_logger.error = AsyncMock()
                mock_logger.warning = AsyncMock()
                
                # Выполнение
                result = await notifier.notify_critical_error("Тестовая ошибка")
        
        # Проверки
        assert result is False
        assert mock_bot.send_message.call_count == 2
        
        # Проверяем логирование
        assert mock_logger.info.call_count == 0  # Нет успешных отправок
        assert mock_logger.error.call_count == 3  # 2 ошибки отправки + 1 общая ошибка
        assert mock_logger.business.call_count == 0  # Нет успешных результатов
    
    @pytest.mark.asyncio
    async def test_notify_critical_error_empty_admin_list(self, notifier, mock_bot):
        """Тест поведения при пустом списке админов"""
        with patch('src.infrastructure.notifications.telegram_notifier.settings') as mock_settings:
            mock_settings.admin_telegram_ids_list = []
            
            with patch('src.infrastructure.notifications.telegram_notifier.hybrid_logger') as mock_logger:
                mock_logger.warning = AsyncMock()
                
                # Выполнение
                result = await notifier.notify_critical_error("Тестовая ошибка")
        
        # Проверки
        assert result is False
        assert mock_bot.send_message.call_count == 0
        assert mock_logger.warning.call_count == 1
    
    @pytest.mark.asyncio
    async def test_notify_critical_error_with_context(self, notifier, mock_bot):
        """Тест отправки критического уведомления с контекстом"""
        admin_ids = [123456789]
        
        with patch('src.infrastructure.notifications.telegram_notifier.settings') as mock_settings:
            mock_settings.admin_telegram_ids_list = admin_ids
            
            with patch('src.infrastructure.notifications.telegram_notifier.hybrid_logger') as mock_logger:
                mock_logger.info = AsyncMock()
                mock_logger.business = AsyncMock()
                
                # Выполнение
                context = {
                    "user_id": 12345,
                    "action": "catalog_search",
                    "error_code": "SEARCH_001"
                }
                result = await notifier.notify_critical_error("Ошибка поиска", context)
        
        # Проверки
        assert result is True
        
        message_text = mock_bot.send_message.call_args.kwargs['text']
        assert "user_id: 12345" in message_text
        assert "action: catalog_search" in message_text
        assert "error_code: SEARCH_001" in message_text
        assert "📊 Контекст:" in message_text
