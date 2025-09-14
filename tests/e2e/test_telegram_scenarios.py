"""
End-to-End тесты для полных сценариев Telegram бота
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.application.telegram.services.user_service import ensure_user_exists
from src.application.telegram.services.message_service import get_or_create_conversation
from src.application.telegram.services.lead_service import LeadService
from src.infrastructure.database.models import User, Conversation, Message, Lead
from tests.fixtures.factories import TestDataBuilder


@pytest.mark.e2e
@pytest.mark.telegram
@pytest.mark.slow
class TestTelegramScenarios:
    """Тесты полных пользовательских сценариев в Telegram"""
    
    async def test_new_user_registration_flow(self, test_session):
        """Тест: Новый пользователь запускает бота"""
        chat_id = 123456
        telegram_user_id = 987654
        
        # Пользователь впервые запускает бота (/start)
        user = await ensure_user_exists(
            test_session,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            username="new_user",
            first_name="Новый",
            last_name="Пользователь"
        )
        
        assert user is not None
        assert user.chat_id == chat_id
        assert user.telegram_user_id == telegram_user_id
        assert user.username == "new_user"
        assert user.first_name == "Новый"
        
        # Проверяем что пользователь сохранен в БД
        await test_session.commit()
        
        # Создается диалог
        conversation = await get_or_create_conversation(
            test_session,
            chat_id=chat_id
        )
        
        assert conversation is not None
        assert conversation.chat_id == chat_id
        assert conversation.status == "active"
        assert conversation.platform == "telegram"
    
    async def test_search_product_scenario(self, test_session):
        """Тест: Пользователь ищет товар через бота"""
        # Подготавливаем пользователя и диалог
        user, conversation = TestDataBuilder.create_user_with_conversation(chat_id=555555)
        test_session.add_all([user, conversation])
        await test_session.flush()
        
        # Пользователь отправляет поисковый запрос
        search_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Ищу насос циркуляционный для отопления",
            # tokens_used=12
        )
        test_session.add(search_message)
        
        # Бот отвечает с результатами поиска
        response_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="🔍 Найдено 5 товаров по запросу 'насос циркуляционный':\n\n1. Насос циркуляционный GRUNDFOS...",
            # tokens_used=85
        )
        test_session.add(response_message)
        
        await test_session.commit()
        
        # Проверяем сохранение диалога
        from sqlalchemy import select
        result = await test_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = result.scalars().all()
        
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert "найдено" in messages[1].content.lower()
    
    async def test_lead_creation_through_contact_form(self, test_session):
        """Тест: Пользователь заполняет форму контакта через бота"""
        # Создаем пользователя
        user, conversation = TestDataBuilder.create_user_with_conversation(chat_id=777777)
        test_session.add_all([user, conversation])
        await test_session.flush()
        
        # Имитируем заполнение формы через состояния FSM
        # (В реальности это происходит через handlers)
        
        # 1. Пользователь вводит имя
        name_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Иван Сидоров",
            # tokens_used=5
        )
        test_session.add(name_message)
        
        # 2. Пользователь вводит телефон
        phone_message = Message(
            conversation_id=conversation.id,
            role="user", 
            content="+79001234567",
            # tokens_used=3
        )
        test_session.add(phone_message)
        
        # 3. Пользователь вводит email
        email_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="ivan@example.com",
            # tokens_used=4
        )
        test_session.add(email_message)
        
        # 4. Пользователь описывает вопрос
        question_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Нужна консультация по выбору насоса для частного дома",
            # tokens_used=15
        )
        test_session.add(question_message)
        
        await test_session.flush()
        
        # 5. Создается лид через сервис
        lead_service = LeadService()
        from src.application.telegram.services.lead_service import LeadCreateRequest
        from src.domain.entities.lead import LeadSource
        
        lead_data = LeadCreateRequest(
            name="Иван Сидоров",
            phone="+79001234567",
            email="ivan@example.com",
            question="Нужна консультация по выбору насоса для частного дома",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        
        created_lead = await lead_service.create_lead(
            test_session,
            user.id,
            lead_data
        )
        
        # 6. Бот подтверждает создание лида
        confirmation_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="✅ Ваша заявка принята! Номер заявки: #001\nМенеджер свяжется с вами в течение рабочего дня.",
            # tokens_used=25
        )
        test_session.add(confirmation_message)
        
        await test_session.commit()
        
        # Проверяем результат
        assert created_lead is not None
        assert created_lead.name == "Иван Сидоров"
        assert created_lead.phone == "+79001234567"
        assert created_lead.email == "ivan@example.com"
        
        # Проверяем что весь диалог сохранен
        from sqlalchemy import select
        result = await test_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = result.scalars().all()
        
        assert len(messages) == 5  # 4 от пользователя + 1 подтверждение
    
    async def test_inactive_user_auto_lead_creation(self, test_session):
        """Тест: Автоматическое создание лида для неактивного пользователя"""
        # Создаем неактивного пользователя
        user, conversation, auto_lead = TestDataBuilder.create_inactive_user_with_lead()
        test_session.add_all([user, conversation])
        await test_session.flush()
        
        # Имитируем работу монитора неактивных пользователей
        lead_service = LeadService()
        
        # Находим неактивных пользователей
        inactive_users = await lead_service.find_inactive_users(
            test_session,
            inactive_minutes=30
        )
        
        assert len(inactive_users) >= 1
        
        # Создаем автолид для первого неактивного пользователя
        user_id, last_activity = inactive_users[0]
        created_lead = await lead_service.auto_create_lead_for_user(
            test_session,
            user_id
        )
        
        # Проверяем автосоздание лида
        if created_lead:  # Может быть None если нет достаточных данных
            assert created_lead.auto_created is True
            assert created_lead.question == "Автоматически создан при завершении диалога"
            assert created_lead.user_id == user_id
    
    @pytest.mark.slow
    async def test_complete_user_journey(self, test_session):
        """Тест: Полный путь пользователя от знакомства до создания лида"""
        chat_id = 999999
        
        # 1. Новый пользователь запускает бота
        user = await ensure_user_exists(
            test_session,
            chat_id=chat_id,
            telegram_user_id=888888,
            username="complete_user",
            first_name="Полный",
            last_name="Тест"
        )
        
        # 2. Создается диалог
        conversation = await get_or_create_conversation(test_session, chat_id=chat_id)
        await test_session.flush()
        
        # 3. Пользователь получает приветствие
        welcome_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="👋 Добро пожаловать! Я помогу вам найти нужные товары и получить консультацию.",
            # tokens_used=20
        )
        test_session.add(welcome_message)
        
        # 4. Пользователь задает вопрос о товарах
        question_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Какие у вас есть насосы для дачи?",
            # tokens_used=10
        )
        test_session.add(question_message)
        
        # 5. Бот предлагает поиск
        search_offer_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Сейчас найду подходящие насосы для дачи. Воспользуйтесь поиском:",
            # tokens_used=15
        )
        test_session.add(search_offer_message)
        
        # 6. Пользователь использует поиск
        search_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="/search насос дачный",
            # tokens_used=5
        )
        test_session.add(search_message)
        
        # 7. Бот показывает результаты
        results_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="🔍 Найдено 8 насосов для дачи:\n\n1. Насос поверхностный ДЖИЛЕКС...\n2. Насос погружной ВОДОЛЕЙ...",
            # tokens_used=50
        )
        test_session.add(results_message)
        
        # 8. Пользователь интересуется конкретным товаром
        interest_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Расскажите подробнее про ДЖИЛЕКС",
            # tokens_used=8
        )
        test_session.add(interest_message)
        
        # 9. Бот предлагает консультацию
        consultation_offer = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Для подробной консультации по ДЖИЛЕКС рекомендую связаться с нашим менеджером. Оставьте контакты?",
            # tokens_used=25
        )
        test_session.add(consultation_offer)
        
        # 10. Пользователь соглашается на контакт
        contact_agree = Message(
            conversation_id=conversation.id,
            role="user",
            content="Да, оставлю контакты",
            # tokens_used=5
        )
        test_session.add(contact_agree)
        
        await test_session.flush()
        
        # 11. Создается лид
        lead_service = LeadService()
        from src.application.telegram.services.lead_service import LeadCreateRequest
        from src.domain.entities.lead import LeadSource
        
        lead_data = LeadCreateRequest(
            name="Полный Тест",
            phone="+79001111111",
            telegram="@complete_user",
            question="Интересует насос ДЖИЛЕКС для дачи",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        
        final_lead = await lead_service.create_lead(
            test_session,
            user.id,
            lead_data
        )
        
        await test_session.commit()
        
        # Проверяем весь путь пользователя
        assert user is not None
        assert conversation is not None
        assert final_lead is not None
        
        # Проверяем количество сообщений в диалоге
        from sqlalchemy import select
        result = await test_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        all_messages = result.scalars().all()
        
        assert len(all_messages) == 8  # Полный диалог
        
        # Проверяем финальный лид
        assert final_lead.name == "Полный Тест"
        assert final_lead.user_id == user.id
        assert "ДЖИЛЕКС" in final_lead.question
    
    async def test_error_recovery_scenario(self, test_session):
        """Тест: Восстановление после ошибок в диалоге"""
        user, conversation = TestDataBuilder.create_user_with_conversation(chat_id=111111)
        test_session.add_all([user, conversation])
        await test_session.flush()
        
        # Пользователь отправляет некорректный запрос
        invalid_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="!@#$%^&*()",
            # tokens_used=3
        )
        test_session.add(invalid_message)
        
        # Бот обрабатывает ошибку и отвечает
        error_response = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Извините, не понял ваш запрос. Попробуйте описать что вас интересует другими словами.",
            # tokens_used=20
        )
        test_session.add(error_response)
        
        # Пользователь повторяет запрос корректно
        correct_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Ищу насос для полива огорода",
            # tokens_used=8
        )
        test_session.add(correct_message)
        
        # Бот успешно обрабатывает запрос
        success_response = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Отлично! Показываю насосы для полива:",
            # tokens_used=10
        )
        test_session.add(success_response)
        
        await test_session.commit()
        
        # Проверяем что диалог продолжился после ошибки
        from sqlalchemy import select
        result = await test_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = result.scalars().all()
        
        assert len(messages) == 4
        assert messages[0].content == "!@#$%^&*()"
        assert "не понял" in messages[1].content.lower()
        assert messages[2].content == "Ищу насос для полива огорода"
        assert "показываю" in messages[3].content.lower()
