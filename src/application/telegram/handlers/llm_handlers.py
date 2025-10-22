"""
LLM обработчики для Telegram бота.
Интегрируют умные ответы через классификацию и маршрутизацию запросов.
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.services import search_orchestrator, is_contact_request
from ..keyboards.search_keyboards import get_contact_manager_keyboard
from ..services.message_service import save_message, get_conversation_history


class LLMHandlers:
    """
    Класс обработчиков для LLM интеграции.
    Обрабатывает все текстовые сообщения через поисковый оркестратор.
    """
    
    def __init__(self) -> None:
        """
        Инициализация LLM обработчиков.
        
        Args:
            message_service: Сервис для работы с сообщениями
        """
        self.router = Router()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Регистрируем handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Регистрирует все обработчики LLM."""
        # Обработчик всех текстовых сообщений (кроме команд)
        self.router.message.register(
            self.handle_text_message,
            F.text & ~F.text.startswith('/')
        )
    
    async def handle_text_message(self, message: Message, session: AsyncSession) -> None:
        """
        Основной обработчик текстовых сообщений.
        Использует LLM для классификации и генерации ответов.
        
        Args:
            message: Сообщение пользователя
            session: Сессия базы данных
        """
        try:
            # Создаем или получаем пользователя
            from ..services.user_service import ensure_user_exists
            await ensure_user_exists(
                session=session,
                chat_id=message.chat.id,
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
            user_text = message.text.strip()
            chat_id = message.chat.id
            
            if not user_text:
                await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
                return
            
            self._logger.info(f"Обработка LLM запроса от пользователя {message.from_user.id}: '{user_text[:50]}...'")
            
            # Показываем индикатор печати
            await message.bot.send_chat_action(chat_id, "typing")
            
            # Обрабатываем запрос через оркестратор
            result = await search_orchestrator.process_user_query(
                user_query=user_text,
                chat_id=chat_id,
                session=session
            )
            
            # Отправляем ответ
            response_text = result["response"]
            query_type = result["query_type"]
            suggested_actions = result.get("suggested_actions", [])
            
            # Добавляем клавиатуру если нужно
            keyboard = None
            if "contact_manager" in suggested_actions or query_type == "CONTACT":
                keyboard = get_contact_manager_keyboard()
            
            # Отправляем ответ с возможной клавиатурой
            await message.answer(
                response_text,
                reply_markup=keyboard
            )
            
            # Логируем результат
            self._logger.info(f"Отправлен LLM ответ типа {query_type}, длина: {len(response_text)} символов")
            
            # Дополнительные действия в зависимости от типа запроса
            await self._handle_post_response_actions(
                message, query_type, suggested_actions, result.get("metadata", {}), session
            )
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки LLM сообщения: {e}")
            await message.answer(
                "❌ Произошла ошибка при обработке вашего запроса. Попробуйте еще раз или свяжитесь с менеджером.",
                reply_markup=get_contact_manager_keyboard()
            )
    
    async def _handle_post_response_actions(
        self,
        message: Message,
        query_type: str,
        suggested_actions: list,
        metadata: dict,
        session: AsyncSession
    ) -> None:
        """
        Выполняет дополнительные действия после отправки ответа.
        
        Args:
            message: Исходное сообщение
            query_type: Тип запроса
            suggested_actions: Предложенные действия
            metadata: Метаданные обработки
            session: Сессия базы данных
        """
        try:
            # Если это запрос на контакт - предлагаем оставить данные
            if query_type == "CONTACT" or "create_lead" in suggested_actions:
                await self._handle_contact_follow_up(message, session)
            
            # Если поиск товаров не дал результатов - предлагаем альтернативы
            if query_type == "PRODUCT" and metadata.get("search_results_count", 0) == 0:
                await self._handle_no_results_follow_up(message)
            
            # Если это первое сообщение пользователя - показываем возможности
            if query_type == "GENERAL" and metadata.get("is_first_message", False):
                await self._show_bot_capabilities(message)
                
        except Exception as e:
            self._logger.error(f"Ошибка выполнения дополнительных действий: {e}")
    
    async def _handle_contact_follow_up(
        self, 
        message: Message, 
        session: AsyncSession
    ) -> None:
        """Дополнительные действия для запросов на контакт."""
        try:
            # Проверяем, есть ли уже контактные данные пользователя
            user_has_contacts = await self._check_user_contacts(
                message.from_user.id, session
            )
            
            if not user_has_contacts:
                follow_up_text = (
                    "💼 Для связи с менеджером, пожалуйста, предоставьте:\n"
                    "• Ваше имя\n"
                    "• Телефон или email\n"
                    "• Краткое описание вопроса\n\n"
                    "Наш менеджер свяжется с вами в ближайшее время!"
                )
                
                await message.answer(follow_up_text)
                
        except Exception as e:
            self._logger.error(f"Ошибка обработки follow-up для контакта: {e}")
    
    async def _handle_no_results_follow_up(self, message: Message) -> None:
        """Дополнительные предложения при отсутствии результатов поиска."""
        try:
            suggestions_text = (
                "🔍 Не нашли то, что искали? Попробуйте:\n\n"
                "• Уточнить запрос (например, указать модель или артикул)\n"
                "• Использовать другие ключевые слова\n"
                "• Связаться с менеджером для персональной консультации\n\n"
                "Наши специалисты помогут найти нужное оборудование!"
            )
            
            await message.answer(
                suggestions_text,
                reply_markup=get_contact_manager_keyboard()
            )
            
        except Exception as e:
            self._logger.error(f"Ошибка отправки предложений: {e}")
    
    async def _show_bot_capabilities(self, message: Message) -> None:
        """Показывает возможности бота новому пользователю."""
        try:
            capabilities_text = (
                "🤖 Я могу помочь вам:\n\n"
                "🔍 Найти товары в каталоге (40,000+ позиций)\n"
                "ℹ️ Рассказать об услугах компании\n"
                "📞 Связать с менеджером для консультации\n"
                "❓ Ответить на общие вопросы\n\n"
                "Просто напишите, что вас интересует!"
            )
            
            await message.answer(capabilities_text)
            
        except Exception as e:
            self._logger.error(f"Ошибка показа возможностей бота: {e}")
    
    async def _check_user_contacts(
        self, 
        telegram_user_id: int, 
        session: AsyncSession
    ) -> bool:
        """
        Проверяет, есть ли контактные данные у пользователя.
        
        Args:
            telegram_user_id: ID пользователя в Telegram
            session: Сессия базы данных
            
        Returns:
            True если есть контактные данные
        """
        try:
            from sqlalchemy import select
            from ....infrastructure.database.models import User
            
            user_query = select(User).where(User.telegram_user_id == telegram_user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if user:
                # Проверяем наличие контактных данных
                has_contacts = bool(
                    user.phone or 
                    user.email or 
                    (user.first_name and user.last_name)
                )
                return has_contacts
            
            return False
            
        except Exception as e:
            self._logger.error(f"Ошибка проверки контактов пользователя: {e}")
            return False


# Функция для создания экземпляра обработчиков
def create_llm_handlers() -> LLMHandlers:
    """
    Создает экземпляр LLM обработчиков.
    
    Args:
        message_service: Сервис для работы с сообщениями
        
    Returns:
        Настроенные LLM обработчики
    """
    return LLMHandlers()
