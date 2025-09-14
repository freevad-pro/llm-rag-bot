"""
Интеграционные тесты для операций с базой данных
"""
import pytest
import random
from datetime import datetime, timedelta
from sqlalchemy import select, and_

from src.infrastructure.database.models import User, Lead, Conversation, Message
from src.application.telegram.services.lead_service import LeadService, LeadCreateRequest

@pytest.fixture
def unique_ids():
    """Генерирует уникальные ID для тестов"""
    base_id = random.randint(10000, 99999)
    return {
        'chat_id': base_id,
        'telegram_user_id': base_id + 1000,
        'chat_id_2': base_id + 10000,
        'telegram_user_id_2': base_id + 11000,
    }

from src.domain.entities.lead import LeadSource, LeadStatus
from tests.fixtures.factories import UserFactory, LeadFactory, TestDataBuilder


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseOperations:
    """Тесты CRUD операций с базой данных"""
    
    async def test_user_creation_and_retrieval(self, test_session, unique_ids):
        """Тест создания и получения пользователя"""
        # Создаем пользователя
        user = User(
            chat_id=unique_ids['chat_id'],
            telegram_user_id=unique_ids['telegram_user_id'],
            username="test_user",
            first_name="Иван",
            last_name="Петров",
            phone="+79001234567",
            email="ivan@example.com"
        )
        
        test_session.add(user)
        await test_session.flush()
        
        # Получаем пользователя по chat_id
        result = await test_session.execute(
            select(User).where(User.chat_id == unique_ids['chat_id'])
        )
        retrieved_user = result.scalar_one_or_none()
        
        assert retrieved_user is not None
        assert retrieved_user.chat_id == unique_ids['chat_id']
        assert retrieved_user.username == "test_user"
        assert retrieved_user.first_name == "Иван"
        assert retrieved_user.last_name == "Петров"
        assert retrieved_user.phone == "+79001234567"
        assert retrieved_user.email == "ivan@example.com"
    
    async def test_lead_creation_with_relationships(self, test_session, unique_ids):
        """Тест создания лида с связями"""
        # Создаем пользователя
        user = User(
            chat_id=unique_ids['chat_id'],
            telegram_user_id=unique_ids['telegram_user_id'],
            username="test_user",
            first_name="Иван",
            last_name="Петров"
        )
        test_session.add(user)
        await test_session.flush()  # Получаем ID пользователя
        
        # Создаем лид
        lead = Lead(
            user_id=user.id,
            name="Иван Петров",
            phone="+79001234567",
            email="ivan@example.com",
            telegram="@test_user",
            company="ООО Тест",
            question="Нужен насос для дома",
            lead_source="Telegram Bot"
        )
        
        test_session.add(lead)
        await test_session.flush()
        
        # Проверяем создание и связи
        result = await test_session.execute(
            select(Lead).where(Lead.user_id == user.id)
        )
        retrieved_lead = result.scalar_one_or_none()
        
        assert retrieved_lead is not None
        assert retrieved_lead.name == "Иван Петров"
        assert retrieved_lead.phone == "+79001234567"
        assert retrieved_lead.user_id == user.id
        assert retrieved_lead.status == "pending_sync"  # Значение по умолчанию
    
    async def test_conversation_and_messages(self, test_session, unique_ids):
        """Тест создания диалога и сообщений"""
        # Создаем пользователя
        user = User(chat_id=unique_ids['chat_id'], telegram_user_id=unique_ids['telegram_user_id'])
        test_session.add(user)
        await test_session.flush()
        
        # Создаем диалог
        conversation = Conversation(
            chat_id=user.chat_id,
            user_id=user.id,
            platform="telegram",
            status="active"
        )
        test_session.add(conversation)
        await test_session.flush()
        
        # Создаем сообщения
        messages = [
            Message(
                conversation_id=conversation.id,
                role="user",
                content="Привет! Нужен насос."
            ),
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content="Здравствуйте! Помогу вам выбрать насос."
            )
        ]
        
        for message in messages:
            test_session.add(message)
        
        await test_session.flush()
        
        # Проверяем создание
        result = await test_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        retrieved_messages = result.scalars().all()
        
        assert len(retrieved_messages) == 2
        assert retrieved_messages[0].role == "user"
        assert retrieved_messages[1].role == "assistant"
    
    async def test_lead_service_integration(self, test_session, unique_ids):
        """Тест интеграции LeadService с базой данных"""
        # Создаем пользователя
        user = User(chat_id=unique_ids['chat_id'], telegram_user_id=unique_ids['telegram_user_id'], first_name="Иван")
        test_session.add(user)
        await test_session.flush()
        
        # Создаем лид через сервис
        lead_service = LeadService()
        lead_data = LeadCreateRequest(
            name="Иван Петров",
            phone="+79001234567",
            email="ivan@example.com",
            company="ООО Тест",
            question="Нужен консультация по насосам",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        
        created_lead = await lead_service.create_lead(
            test_session, 
            user.id, 
            lead_data
        )
        
        # Проверяем создание
        assert created_lead is not None
        assert created_lead.name == "Иван Петров"
        assert created_lead.phone == "+79001234567"
        assert created_lead.user_id == user.id
        assert created_lead.status == LeadStatus.PENDING_SYNC
        
        # Проверяем сохранение в БД
        result = await test_session.execute(
            select(Lead).where(Lead.user_id == user.id)
        )
        db_lead = result.scalar_one_or_none()
        
        assert db_lead is not None
        assert db_lead.name == "Иван Петров"
    
    async def test_find_inactive_users(self, test_session, unique_ids):
        """Тест поиска неактивных пользователей"""
        # Создаем активного пользователя (недавняя активность)
        active_user = User(chat_id=unique_ids['chat_id'], telegram_user_id=unique_ids['telegram_user_id'])
        test_session.add(active_user)
        await test_session.flush()
        
        active_conversation = Conversation(
            chat_id=active_user.chat_id,
            user_id=active_user.id,
            status="active",
            started_at=datetime.utcnow() - timedelta(minutes=10)  # 10 минут назад
        )
        test_session.add(active_conversation)
        
        # Создаем неактивного пользователя (старая активность)
        inactive_user = User(chat_id=unique_ids['chat_id_2'], telegram_user_id=unique_ids['telegram_user_id_2'])
        test_session.add(inactive_user)
        await test_session.flush()
        
        inactive_conversation = Conversation(
            chat_id=inactive_user.chat_id,
            user_id=inactive_user.id,
            status="active",
            started_at=datetime.utcnow() - timedelta(hours=2)  # 2 часа назад
        )
        test_session.add(inactive_conversation)
        
        await test_session.flush()
        
        # Ищем неактивных пользователей (неактивность > 60 минут)
        lead_service = LeadService()
        inactive_users = await lead_service.find_inactive_users(
            test_session, 
            inactive_minutes=60
        )
        
        # Должен найтись только неактивный пользователь
        assert len(inactive_users) == 1
        user_id, last_activity = inactive_users[0]
        assert user_id == inactive_user.id
    
    async def test_auto_create_lead_for_user(self, test_session, unique_ids):
        """Тест автоматического создания лида для пользователя"""
        # Создаем пользователя с полными данными
        user = User(
            chat_id=unique_ids['chat_id'],
            telegram_user_id=unique_ids['telegram_user_id'],
            username="test_user",
            first_name="Иван",
            last_name="Петров",
            phone="+79001234567",
            email="ivan@example.com"
        )
        test_session.add(user)
        await test_session.flush()
        
        # Автоматически создаем лид
        lead_service = LeadService()
        created_lead = await lead_service.auto_create_lead_for_user(
            test_session,
            user.id
        )
        
        # Проверяем создание
        assert created_lead is not None
        assert created_lead.name == "Иван Петров"
        assert created_lead.phone == "+79001234567"
        assert created_lead.auto_created is True
        assert created_lead.question == "Автоматически создан при завершении диалога"
        
        # Проверяем, что повторное создание не происходит
        second_lead = await lead_service.auto_create_lead_for_user(
            test_session,
            user.id
        )
        
        assert second_lead is None  # Уже есть недавний лид
    
    async def test_database_constraints(self, test_session, unique_ids):
        """Тест ограничений базы данных"""
        # Тест уникальности chat_id
        user1 = User(chat_id=unique_ids['chat_id'], telegram_user_id=unique_ids['telegram_user_id'])
        user2 = User(chat_id=unique_ids['chat_id'], telegram_user_id=unique_ids['telegram_user_id_2'])  # Тот же chat_id
        
        test_session.add(user1)
        test_session.add(user2)
        
        # Должна возникнуть ошибка уникальности
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            await test_session.flush()
    
    @pytest.mark.slow
    async def test_large_dataset_performance(self, test_session, unique_ids):
        """Тест производительности на большом объеме данных"""
        # Создаем много пользователей и лидов
        users = []
        for i in range(100):
            user = User(
                chat_id=unique_ids['chat_id'] + i,
                telegram_user_id=unique_ids['telegram_user_id'] + i,
                username=f"user_{i}",
                first_name=f"User{i}"
            )
            users.append(user)
            test_session.add(user)
        
        await test_session.flush()
        
        # Создаем лиды для каждого пользователя
        leads = []
        for i, user in enumerate(users):
            lead = Lead(
                user_id=user.id,
                name=f"Lead {i}",
                phone=f"+7900123{i:04d}",
                email=f"lead{i}@example.com",
                lead_source="Telegram Bot"
            )
            leads.append(lead)
            test_session.add(lead)
        
        await test_session.flush()
        
        # Тестируем быстрый поиск по индексам
        start_time = datetime.utcnow()
        
        result = await test_session.execute(
            select(Lead).where(
                and_(
                    Lead.status == "pending_sync",
                    Lead.name.like("Lead %")  # Только наши лиды из этого теста
                )
            )
        )
        pending_leads = result.scalars().all()
        
        end_time = datetime.utcnow()
        query_time = (end_time - start_time).total_seconds()
        
        # Запрос должен выполняться быстро (< 0.1 секунды)
        assert query_time < 0.1
        assert len(pending_leads) == 100  # Все лиды из этого теста в статусе pending_sync
