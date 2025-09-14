"""
Фабрики для создания тестовых данных с помощью factory_boy
"""
import factory
from factory import SubFactory, LazyAttribute, Faker
from faker import Faker as FakerInstance
from datetime import datetime
from typing import Optional

# Создаем экземпляр Faker для использования в LazyFunction
fake = FakerInstance('ru_RU')

from src.infrastructure.database.models import User, Lead, Conversation, Message, LLMSetting
from src.domain.entities.lead import LeadStatus, LeadSource


class UserFactory(factory.Factory):
    """Фабрика для создания пользователей"""
    class Meta:
        model = User

    id = factory.Sequence(lambda n: 10000 + n)
    chat_id = factory.Sequence(lambda n: 1000000 + n)
    telegram_user_id = factory.Sequence(lambda n: 500000 + n)
    username = factory.LazyAttribute(lambda obj: f"user_{obj.chat_id}")
    first_name = Faker('first_name', locale='ru_RU')
    last_name = Faker('last_name', locale='ru_RU')
    phone = factory.LazyFunction(lambda: f"+7{fake.random_int(min=9000000000, max=9999999999)}")
    email = Faker('email')
    created_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def create_with_chat_id(cls, chat_id: int, **kwargs):
        """Создает пользователя с конкретным chat_id"""
        return cls(chat_id=chat_id, **kwargs)


class LeadFactory(factory.Factory):
    """Фабрика для создания лидов"""
    class Meta:
        model = Lead

    id = factory.Sequence(lambda n: 20000 + n)
    user_id = factory.SubFactory(UserFactory)
    name = factory.LazyAttribute(lambda obj: f"{fake.first_name()} {fake.last_name()}")
    phone = factory.LazyFunction(lambda: f"+7{fake.random_int(min=9000000000, max=9999999999)}")
    email = Faker('email')
    telegram = factory.LazyAttribute(lambda obj: f"@user_{fake.random_int(min=1000, max=9999)}")
    company = Faker('company', locale='ru_RU')
    question = Faker('text', max_nb_chars=200, locale='ru_RU')
    status = LeadStatus.PENDING_SYNC.value
    sync_attempts = 0
    zoho_lead_id = None
    last_sync_attempt = None
    auto_created = False
    lead_source = LeadSource.TELEGRAM_BOT.value
    created_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def create_auto_lead(cls, **kwargs):
        """Создает автоматически созданный лид"""
        return cls(
            auto_created=True,
            question="Автоматически создан при завершении диалога",
            **kwargs
        )

    @classmethod
    def create_synced_lead(cls, **kwargs):
        """Создает синхронизированный лид"""
        return cls(
            status=LeadStatus.SYNCED.value,
            zoho_lead_id=f"zoho_{fake.random_int(min=1000000, max=9999999)}",
            **kwargs
        )


class ConversationFactory(factory.Factory):
    """Фабрика для создания диалогов"""
    class Meta:
        model = Conversation

    id = factory.Sequence(lambda n: 30000 + n)
    chat_id = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute('chat_id.id')
    platform = "telegram"
    status = "active"
    started_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def create_inactive(cls, **kwargs):
        """Создает неактивный диалог"""
        from datetime import timedelta
        past_time = datetime.utcnow() - timedelta(hours=2)
        return cls(
            status="inactive",
            started_at=past_time,
            **kwargs
        )


class MessageFactory(factory.Factory):
    """Фабрика для создания сообщений"""
    class Meta:
        model = Message

    id = factory.Sequence(lambda n: 40000 + n)
    conversation_id = factory.SubFactory(ConversationFactory)
    role = "user"
    content = Faker('sentence', nb_words=10, locale='ru_RU')
    created_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def create_bot_message(cls, **kwargs):
        """Создает сообщение от бота"""
        return cls(
            role="assistant",
            content=fake.paragraph(nb_sentences=3),
            **kwargs
        )

    @classmethod
    def create_search_query(cls, **kwargs):
        """Создает поисковый запрос"""
        search_queries = [
            "Ищу насос для дома",
            "Нужны фитинги 32мм",
            "Какие двигатели есть в наличии?",
            "Крепеж для труб ПНД",
            "Муфты соединительные"
        ]
        return cls(
            content=fake.random_element(elements=search_queries),
            **kwargs
        )


class LLMSettingFactory(factory.Factory):
    """Фабрика для настроек LLM"""
    class Meta:
        model = LLMSetting

    id = factory.Sequence(lambda n: 50000 + n)
    provider = "openai"
    config = factory.LazyFunction(lambda: '{"api_key": "test_key", "model": "gpt-3.5-turbo"}')
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def create_yandex(cls, **kwargs):
        """Создает настройки для YandexGPT"""
        return cls(
            provider="yandex",
            config='{"api_key": "test_yandex_key", "folder_id": "test_folder"}',
            **kwargs
        )


# Утилиты для создания наборов тестовых данных
class TestDataBuilder:
    """Помощник для создания связанных тестовых данных"""
    
    @staticmethod
    def create_user_with_conversation(chat_id: int = None):
        """Создает пользователя с активным диалогом"""
        user = UserFactory.create_with_chat_id(chat_id or 123456)
        conversation = ConversationFactory(chat_id=user.chat_id, user_id=user.id)
        return user, conversation
    
    @staticmethod
    def create_full_dialog(messages_count: int = 5):
        """Создает полный диалог с пользователем и сообщениями"""
        user, conversation = TestDataBuilder.create_user_with_conversation()
        
        messages = []
        for i in range(messages_count):
            # Чередуем сообщения от пользователя и бота
            if i % 2 == 0:
                message = MessageFactory(conversation_id=conversation.id)
            else:
                message = MessageFactory.create_bot_message(conversation_id=conversation.id)
            messages.append(message)
        
        return user, conversation, messages
    
    @staticmethod
    def create_inactive_user_with_lead():
        """Создает неактивного пользователя с лидом"""
        user = UserFactory()
        conversation = ConversationFactory.create_inactive(
            chat_id=user.chat_id, 
            user_id=user.id
        )
        lead = LeadFactory.create_auto_lead(user_id=user.id)
        return user, conversation, lead
    
    @staticmethod
    def create_search_scenario():
        """Создает сценарий поиска товаров"""
        user, conversation = TestDataBuilder.create_user_with_conversation()
        
        # Пользователь делает поисковый запрос
        search_message = MessageFactory.create_search_query(conversation_id=conversation.id)
        
        # Бот отвечает с результатами
        response_message = MessageFactory.create_bot_message(
            conversation_id=conversation.id,
            content="Найдено 5 товаров по вашему запросу:\n1. Насос циркуляционный..."
        )
        
        return user, conversation, [search_message, response_message]


# Экспорт всех фабрик для удобного импорта
__all__ = [
    'UserFactory',
    'LeadFactory', 
    'ConversationFactory',
    'MessageFactory',
    'LLMSettingFactory',
    'TestDataBuilder'
]
