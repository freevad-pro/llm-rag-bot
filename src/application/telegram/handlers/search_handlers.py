"""
Обработчики поиска товаров для Telegram бота.
Реализует команды и callback'и для работы с каталогом.
"""

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.search.catalog_service import CatalogSearchService
from ..keyboards.search_keyboards import SearchKeyboardBuilder, get_main_search_keyboard, get_contact_manager_keyboard
from ..services import message_service

logger = logging.getLogger(__name__)

# FSM состояния для поиска
class SearchStates(StatesGroup):
    waiting_for_search_query = State()
    waiting_for_article_search = State()


class SearchHandlers:
    """
    Класс обработчиков поиска товаров.
    """
    
    def __init__(
        self, 
        catalog_service: CatalogSearchService
    ) -> None:
        """
        Инициализация обработчиков поиска.
        
        Args:
            catalog_service: Сервис поиска по каталогу
        """
        self.catalog_service = catalog_service
        self.router = Router()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Регистрируем handlers
        self._register_handlers()
    
    async def save_user_message(self, session: AsyncSession, user_id: int, chat_id: int, content: str) -> None:
        """Обёртка для сохранения сообщения пользователя"""
        await message_service.save_message(session, chat_id, "user", content)
    
    async def save_assistant_message(self, session: AsyncSession, user_id: int, chat_id: int, content: str) -> None:
        """Обёртка для сохранения сообщения ассистента"""
        await message_service.save_message(session, chat_id, "assistant", content)
    
    def _register_handlers(self) -> None:
        """Регистрирует все обработчики поиска."""
        
        # Команды
        self.router.message(Command("search"))(self.cmd_search)
        self.router.message(Command("categories"))(self.cmd_categories)
        
        # Callback'и для поиска
        self.router.callback_query(F.data == "new_search")(self.callback_new_search)
        self.router.callback_query(F.data == "search_by_name")(self.callback_search_by_name)
        self.router.callback_query(F.data == "search_by_categories")(self.callback_search_by_categories)
        self.router.callback_query(F.data == "search_by_article")(self.callback_search_by_article)
        self.router.callback_query(F.data == "search_all_categories")(self.callback_search_all_categories)
        
        # Callback'и для категорий
        self.router.callback_query(F.data.startswith("search_category:"))(self.callback_search_category)
        self.router.callback_query(F.data.startswith("categories_page:"))(self.callback_categories_page)
        
        # Callback'и для результатов поиска
        self.router.callback_query(F.data.startswith("search_results_page:"))(self.callback_search_results_page)
        self.router.callback_query(F.data.startswith("product_details:"))(self.callback_product_details)
        self.router.callback_query(F.data.startswith("product_photo:"))(self.callback_product_photo)
        self.router.callback_query(F.data.startswith("product_page:"))(self.callback_product_page)
        
        # Callback'и для действий с товарами
        self.router.callback_query(F.data.startswith("order_product:"))(self.callback_order_product)
        self.router.callback_query(F.data.startswith("ask_about_product:"))(self.callback_ask_about_product)
        
        # Обработка состояний поиска
        self.router.message(SearchStates.waiting_for_search_query)(self.handle_search_query)
        self.router.message(SearchStates.waiting_for_article_search)(self.handle_article_search)
    
    async def cmd_search(self, message: Message, state: FSMContext, session: AsyncSession) -> None:
        """
        Обработчик команды /search.
        
        Args:
            message: Сообщение пользователя
            state: Состояние FSM
        """
        try:
            # Сохраняем сообщение в истории
            await self.save_user_message(
                session,
                message.from_user.id, 
                message.chat.id,
                message.text or ""
            )
            
            # Проверяем индексацию каталога
            if not await self.catalog_service.is_indexed():
                await message.answer(
                    "🔧 Каталог товаров пока не загружен. "
                    "Обратитесь к администратору для индексации каталога.",
                    reply_markup=get_contact_manager_keyboard()
                )
                return
            
            # Показываем меню поиска
            response_text = (
                "🔍 <b>Поиск товаров</b>\n\n"
                "Выберите способ поиска:"
            )
            
            await message.answer(
                response_text,
                reply_markup=get_main_search_keyboard(),
                parse_mode="HTML"
            )
            
            # Сохраняем ответ бота
            await self.save_assistant_message(
                session,
                message.from_user.id,
                message.chat.id, 
                response_text
            )
            
        except Exception as e:
            self._logger.error(f"Ошибка в команде /search: {e}")
            await message.answer(
                "❌ Произошла ошибка при открытии поиска. Попробуйте позже."
            )
    
    async def cmd_categories(self, message: Message, state: FSMContext, session: AsyncSession) -> None:
        """
        Обработчик команды /categories.
        
        Args:
            message: Сообщение пользователя
            state: Состояние FSM
        """
        try:
            # Сохраняем сообщение
            await self.save_user_message(
                session,
                message.from_user.id,
                message.chat.id,
                message.text or ""
            )
            
            await self._show_categories(message.from_user.id, message.chat.id)
            
        except Exception as e:
            self._logger.error(f"Ошибка в команде /categories: {e}")
            await message.answer("❌ Ошибка загрузки категорий.")
    
    async def callback_new_search(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик callback'а нового поиска."""
        await callback.answer()
        await state.clear()
        
        response_text = (
            "🔍 <b>Новый поиск</b>\n\n"
            "Выберите способ поиска:"
        )
        
        await callback.message.edit_text(
            response_text,
            reply_markup=get_main_search_keyboard(),
            parse_mode="HTML"
        )
    
    async def callback_search_by_name(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик поиска по названию."""
        await callback.answer()
        
        await state.set_state(SearchStates.waiting_for_search_query)
        
        response_text = (
            "🔍 <b>Поиск по названию</b>\n\n"
            "Введите название товара или его описание:"
        )
        
        await callback.message.edit_text(response_text, parse_mode="HTML")
    
    async def callback_search_by_categories(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик поиска по категориям."""
        await callback.answer()
        await state.clear()
        
        await self._show_categories(callback.from_user.id, callback.message.chat.id, callback.message)
    
    async def callback_search_by_article(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик поиска по артикулу."""
        await callback.answer()
        
        await state.set_state(SearchStates.waiting_for_article_search)
        
        response_text = (
            "🆔 <b>Поиск по артикулу</b>\n\n"
            "Введите артикул товара:"
        )
        
        await callback.message.edit_text(response_text, parse_mode="HTML")

    async def callback_search_all_categories(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик поиска по всем категориям."""
        await callback.answer()
        
        await callback.message.edit_text(
            "📂 <b>Все категории</b>\n\n"
            "Выберите категорию или введите название товара:",
            parse_mode="HTML",
            reply_markup=SearchKeyboardBuilder.back_to_search_menu()
        )
        
        # Показываем все категории
        await self._show_categories(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message=callback.message,
            page=0
        )
    
    async def callback_search_category(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик поиска в конкретной категории."""
        await callback.answer()
        
        # Извлекаем категорию из callback_data
        category = callback.data.split(":", 1)[1]
        
        await state.set_state(SearchStates.waiting_for_search_query)
        await state.update_data(category=category)
        
        response_text = (
            f"🔍 <b>Поиск в категории:</b> {category}\n\n"
            "Введите поисковый запрос:"
        )
        
        await callback.message.edit_text(response_text, parse_mode="HTML")
    
    async def callback_categories_page(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик пагинации категорий."""
        await callback.answer()
        
        # Извлекаем номер страницы
        page = int(callback.data.split(":")[1])
        
        await self._show_categories(
            callback.from_user.id, 
            callback.message.chat.id, 
            callback.message,
            page
        )
    
    async def handle_search_query(self, message: Message, state: FSMContext, session: AsyncSession) -> None:
        """
        Обработчик поискового запроса.
        
        Args:
            message: Сообщение с запросом
            state: Состояние FSM
        """
        try:
            query = message.text.strip()
            
            if not query:
                await message.answer("❌ Пожалуйста, введите поисковый запрос.")
                return
            
            # Сохраняем сообщение пользователя
            await self.save_user_message(
                session,
                message.from_user.id,
                message.chat.id,
                query
            )
            
            # Получаем данные состояния
            state_data = await state.get_data()
            category = state_data.get("category")
            
            # Выполняем поиск
            await self._perform_search(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                query=query,
                category=category,
                message=message
            )
            
            await state.clear()
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки поискового запроса: {e}")
            await message.answer("❌ Ошибка поиска. Попробуйте еще раз.")
    
    async def handle_article_search(self, message: Message, state: FSMContext, session: AsyncSession) -> None:
        """
        Обработчик поиска по артикулу.
        
        Args:
            message: Сообщение с артикулом
            state: Состояние FSM
        """
        try:
            article = message.text.strip()
            
            if not article:
                await message.answer("❌ Пожалуйста, введите артикул товара.")
                return
            
            # Сохраняем сообщение пользователя
            await self.save_user_message(
                session,
                message.from_user.id,
                message.chat.id,
                article
            )
            
            # Поиск по артикулу (используем как обычный запрос)
            await self._perform_search(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                query=f"артикул {article}",
                category=None,
                message=message
            )
            
            await state.clear()
            
        except Exception as e:
            self._logger.error(f"Ошибка поиска по артикулу: {e}")
            await message.answer("❌ Ошибка поиска. Попробуйте еще раз."        )

    async def callback_search_results_page(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик пагинации результатов поиска."""
        await callback.answer()
        
        # Извлекаем номер страницы из callback_data
        try:
            page = int(callback.data.split(":", 1)[1])
        except (ValueError, IndexError):
            page = 0
        
        # Здесь будет логика загрузки следующей страницы результатов
        # Пока показываем заглушку
        await callback.message.edit_text(
            f"📄 <b>Страница результатов: {page + 1}</b>\n\n"
            "Пагинация результатов поиска будет реализована в следующих итерациях.",
            parse_mode="HTML",
            reply_markup=SearchKeyboardBuilder.back_to_search_menu()
        )
    
    async def callback_product_details(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик показа деталей товара."""
        await callback.answer()
        
        # Извлекаем ID товара
        product_id = callback.data.split(":", 1)[1]
        
        # Здесь можно добавить получение детальной информации о товаре
        # Пока показываем заглушку
        await callback.message.edit_text(
            f"📦 <b>Товар ID: {product_id}</b>\n\n"
            "Детальная информация о товаре будет доступна в следующих итерациях.",
            parse_mode="HTML",
            reply_markup=SearchKeyboardBuilder.build_product_details_keyboard(
                product_id=product_id,
                has_photo=False,
                has_page_url=False
            )
        )
    
    async def callback_order_product(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик заказа товара."""
        await callback.answer("📋 Переход к оформлению заказа...")
        
        # Здесь будет логика создания лида
        await callback.message.answer(
            "💼 <b>Оформление заказа</b>\n\n"
            "Для оформления заказа свяжитесь с нашим менеджером.",
            parse_mode="HTML",
            reply_markup=get_contact_manager_keyboard()
        )
    
    async def _show_categories(
        self, 
        user_id: int, 
        chat_id: int, 
        message: Optional[Message] = None,
        page: int = 0
    ) -> None:
        """
        Показывает категории товаров.
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            message: Сообщение для редактирования (опционально)
            page: Номер страницы
        """
        try:
            # Получаем категории
            categories = await self.catalog_service.get_categories()
            
            if not categories:
                response_text = (
                    "📂 <b>Категории товаров</b>\n\n"
                    "❌ Категории не найдены. Каталог пока не загружен."
                )
                keyboard = get_contact_manager_keyboard()
            else:
                response_text = (
                    f"📂 <b>Категории товаров</b>\n\n"
                    f"Найдено {len(categories)} категорий:"
                )
                keyboard = SearchKeyboardBuilder.build_categories_keyboard(categories, page)
            
            if message:
                # Редактируем существующее сообщение
                await message.edit_text(
                    response_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                # Отправляем новое сообщение
                from aiogram import Bot
                bot = Bot.get_current()
                sent_message = await bot.send_message(
                    chat_id=chat_id,
                    text=response_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                
                # Сохраняем ответ бота (требуется session)
                # await self.save_assistant_message(session, user_id, chat_id, response_text)
            
        except Exception as e:
            self._logger.error(f"Ошибка показа категорий: {e}")
            error_text = "❌ Ошибка загрузки категорий."
            
            if message:
                await message.edit_text(error_text)
            else:
                from aiogram import Bot
                bot = Bot.get_current()
                await bot.send_message(chat_id=chat_id, text=error_text)
    
    async def _perform_search(
        self,
        user_id: int,
        chat_id: int, 
        query: str,
        category: Optional[str] = None,
        message: Optional[Message] = None
    ) -> None:
        """
        Выполняет поиск товаров и показывает результаты.
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            query: Поисковый запрос
            category: Категория для фильтрации
            message: Сообщение пользователя
        """
        try:
            # Показываем индикатор загрузки
            if message:
                loading_msg = await message.answer("🔍 Ищу товары...")
            
            # Выполняем поиск
            search_results = await self.catalog_service.search_products(
                query=query,
                category=category,
                k=20  # Получаем больше результатов для пагинации
            )
            
            # Удаляем индикатор загрузки
            if message:
                await loading_msg.delete()
            
            # Формируем ответ
            if not search_results:
                response_text = (
                    f"🔍 <b>Поиск:</b> {query}\n"
                    f"📂 <b>Категория:</b> {category or 'Все'}\n\n"
                    "❌ <b>Ничего не найдено</b>\n\n"
                    "Попробуйте изменить запрос или выбрать другую категорию."
                )
                
                keyboard = SearchKeyboardBuilder.build_no_results_keyboard(query)
            else:
                # Показываем результаты
                results_count = len(search_results)
                response_text = (
                    f"🔍 <b>Поиск:</b> {query}\n"
                    f"📂 <b>Категория:</b> {category or 'Все'}\n\n"
                    f"✅ <b>Найдено:</b> {results_count} товаров\n\n"
                    "Выберите товар для подробной информации:"
                )
                
                keyboard = SearchKeyboardBuilder.build_search_results_keyboard(
                    search_results=search_results,
                    current_page=0,
                    query=query,
                    category=category
                )
            
            # Отправляем результат
            if message:
                await message.answer(
                    response_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            # Сохраняем ответ бота (требуется session)
            # await self.save_assistant_message(session, user_id, chat_id, response_text)
            
        except Exception as e:
            self._logger.error(f"Ошибка выполнения поиска: {e}")
            error_text = "❌ Ошибка поиска. Попробуйте позже."
            
            if message:
                await message.answer(error_text)
            
            # await self.save_assistant_message(session, user_id, chat_id, error_text)

    async def callback_product_photo(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик показа фото товара."""
        await callback.answer()
        
        product_id = callback.data.split(":", 1)[1]
        await callback.message.edit_text(
            f"📷 <b>Фото товара ID: {product_id}</b>\n\n"
            "Просмотр фотографий товара будет доступен в следующих итерациях.",
            parse_mode="HTML",
            reply_markup=SearchKeyboardBuilder.back_to_search_menu()
        )

    async def callback_product_page(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик перехода на страницу товара."""
        await callback.answer()
        
        product_id = callback.data.split(":", 1)[1]
        await callback.message.edit_text(
            f"🌐 <b>Страница товара ID: {product_id}</b>\n\n"
            "Переход на веб-страницу товара будет доступен в следующих итерациях.",
            parse_mode="HTML",
            reply_markup=SearchKeyboardBuilder.back_to_search_menu()
        )

    async def callback_ask_about_product(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработчик вопроса о товаре."""
        await callback.answer()
        
        product_id = callback.data.split(":", 1)[1]
        await callback.message.edit_text(
            f"❓ <b>Вопрос о товаре ID: {product_id}</b>\n\n"
            "Задать вопрос о товаре менеджеру будет доступно в следующих итерациях.",
            parse_mode="HTML",
            reply_markup=SearchKeyboardBuilder.back_to_search_menu()
        )
