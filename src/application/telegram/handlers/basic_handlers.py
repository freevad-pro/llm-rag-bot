"""
Базовые обработчики команд для Telegram бота
Реализует /start, /help, /contact согласно @vision.md
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.application.telegram.services.user_service import ensure_user_exists
from src.application.telegram.services.message_service import save_message
from src.application.telegram.keyboards.lead_keyboards import (
    get_main_reply_keyboard, 
    get_menu_reply_keyboard
)


router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession):
    """
    Обработчик команды /start
    Регистрирует пользователя и показывает приветствие
    """
    try:
        # Создаем или получаем пользователя
        user = await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем команду в историю
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        # Приветственное сообщение
        welcome_text = f"""
👋 <b>Добро пожаловать!</b>

Я - AI-ассистент для консультации по каталогу товаров и услуг.

<b>Что я умею:</b>
• Поиск товаров по описанию
• Консультации по услугам компании  
• Помощь в выборе оборудования
• Связь с менеджерами

<b>Доступные команды:</b>
/help - справка по использованию
/contact - связаться с менеджером

Просто напишите, что вас интересует! 🔍
        """
        
        # Reply клавиатура с кнопкой Меню
        keyboard = get_main_reply_keyboard()
        
        # Отправляем ответ
        sent_message = await message.answer(
            welcome_text,
            reply_markup=keyboard
        )
        
        # Сохраняем ответ бота
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant", 
            content=welcome_text
        )
        
        # Логируем начало нового чата
        await hybrid_logger.business(
            f"Новый чат: {user.chat_id}",
            {"username": user.username, "first_name": user.first_name}
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(Command("help"))
async def handle_help(message: Message, session: AsyncSession):
    """Обработчик команды /help"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем команду
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        help_text = """
<b>📖 Справка по использованию бота</b>

<b>🔍 Поиск товаров:</b>
Просто опишите, что ищете:
• "Нужен насос для воды"
• "Болты М12 оцинкованные"
• "Электродвигатель 3 кВт"

<b>💬 Консультации:</b>
Задавайте вопросы о:
• Технических характеристиках
• Совместимости оборудования
• Условиях поставки
• Ценах и наличии

<b>📞 Связь с менеджером:</b>
Используйте команду /contact или кнопку в меню

<b>⚡ Быстрые команды:</b>
/start - начать работу
/search - поиск товаров
/categories - категории товаров
/help - эта справка
/contact - связаться с менеджером

Я работаю 24/7 и отвечу в течение нескольких секунд! 🚀
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Поиск товаров", callback_data="new_search"),
                InlineKeyboardButton(text="📂 Категории", callback_data="search_by_categories")
            ],
            [InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="contact_manager")]
        ])
        
        sent_message = await message.answer(help_text, reply_markup=keyboard)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=help_text
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_help: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(Command("contact"))
async def handle_contact(message: Message, session: AsyncSession):
    """Обработчик команды /contact"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем команду
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        contact_text = """
<b>📞 Связь с менеджером</b>

Для персональной консультации с нашим менеджером, пожалуйста, оставьте ваши контактные данные:

<b>Обязательные поля:</b>
• Ваше имя
• Телефон ИЛИ email

<b>Дополнительно:</b>
• Название компании
• Ваш вопрос

Просто напишите сообщение в формате:
"Иван Петров, +7(999)123-45-67, ООО Ромашка, нужен насос для котельной"

Менеджер свяжется с вами в течение рабочего дня! 📧
        """
        
        sent_message = await message.answer(contact_text)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=contact_text
        )
        
        # Логируем запрос на связь
        await hybrid_logger.business(
            "Запрос связи с менеджером",
            {"chat_id": message.chat.id, "username": message.from_user.username}
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_contact: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


# Старый обработчик handle_text_message удален - функционал перенесен в llm_handlers.py
# Это предотвращает конфликт обработчиков и позволяет командам работать корректно


# Обработчик callback запросов от inline кнопок
@router.callback_query(F.data == "help")
async def callback_help(callback_query, session: AsyncSession, state: FSMContext):
    """Обработчик callback для кнопки помощи"""
    await hybrid_logger.debug(f"🔘 Обработчик callback_help вызван для пользователя {callback_query.from_user.id}")
    await callback_query.answer()
    
    # Очищаем состояние FSM при переходе к справке
    await state.clear()
    
    # Вызываем обработчик help через имитацию команды
    fake_message = type('obj', (object,), {
        'chat': callback_query.message.chat,
        'from_user': callback_query.from_user,
        'text': '/help'
    })
    
    await handle_help(fake_message, session)


@router.callback_query(F.data == "contact_manager")
async def callback_contact(callback_query, session: AsyncSession, state: FSMContext):
    """Обработчик callback для кнопки связи с менеджером"""
    await hybrid_logger.debug(f"🔘 Обработчик callback_contact вызван для пользователя {callback_query.from_user.id}")
    await callback_query.answer("Переключаю на связь с менеджером...")
    
    # Очищаем состояние FSM при переходе к контактам
    await state.clear()
    
    # Вызываем обработчик contact
    fake_message = type('obj', (object,), {
        'chat': callback_query.message.chat,
        'from_user': callback_query.from_user,
        'text': '/contact'
    })
    
    await handle_contact(fake_message, session)


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback_query, session: AsyncSession, state: FSMContext):
    """Обработчик callback для кнопки Главное меню"""
    await hybrid_logger.debug(f"🔘 Обработчик callback_main_menu вызван для пользователя {callback_query.from_user.id}")
    await callback_query.answer("Возврат в главное меню...")
    
    # Очищаем состояние FSM при возврате в главное меню
    await state.clear()
    
    # Вызываем обработчик start
    fake_message = type('obj', (object,), {
        'chat': callback_query.message.chat,
        'from_user': callback_query.from_user,
        'text': '/start',
        'answer': callback_query.message.edit_text
    })
    
    await handle_start(fake_message, session)


@router.callback_query(F.data == "leave_contacts")
async def callback_leave_contacts(callback_query, session: AsyncSession):
    """Обработчик callback для кнопки Оставить контакты"""
    await hybrid_logger.debug(f"🔘 Обработчик callback_leave_contacts вызван для пользователя {callback_query.from_user.id}")
    await callback_query.answer("Переход к форме контактов...")
    
    # Вызываем обработчик contact для создания заявки
    fake_message = type('obj', (object,), {
        'chat': callback_query.message.chat,
        'from_user': callback_query.from_user,
        'text': '/contact',
        'answer': callback_query.message.edit_text
    })
    
    await handle_contact(fake_message, session)


# Обработчики для Reply Keyboard кнопок
@router.message(F.text == "📋 Меню")
async def handle_menu_button(message: Message, session: AsyncSession):
    """Обработчик кнопки Меню"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем сообщение
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        menu_text = """
<b>📋 Главное меню</b>

Выберите нужное действие:
        """
        
        # Показываем клавиатуру с опциями меню
        keyboard = get_menu_reply_keyboard()
        
        await message.answer(menu_text, reply_markup=keyboard)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=menu_text
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_menu_button: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "🔍 Поиск товаров")
async def handle_search_button(message: Message, session: AsyncSession):
    """Обработчик кнопки Поиск товаров"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем сообщение
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        search_text = """
<b>🔍 Поиск товаров</b>

Опишите, что вы ищете:
• "Нужен насос для воды"
• "Болты М12 оцинкованные" 
• "Электродвигатель 3 кВт"

Просто напишите ваш запрос, и я найду подходящие товары! 🚀
        """
        
        # Возвращаемся к основной клавиатуре
        keyboard = get_main_reply_keyboard()
        
        await message.answer(search_text, reply_markup=keyboard)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=search_text
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_search_button: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "📞 Связаться с менеджером")
async def handle_contact_button(message: Message, session: AsyncSession):
    """Обработчик кнопки Связаться с менеджером"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем сообщение
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        contact_text = """
<b>📞 Связь с менеджером</b>

Для персональной консультации с нашим менеджером, пожалуйста, оставьте ваши контактные данные:

<b>Обязательные поля:</b>
• Ваше имя
• Телефон ИЛИ email

<b>Дополнительно:</b>
• Название компании
• Ваш вопрос

Просто напишите сообщение в формате:
"Иван Петров, +7(999)123-45-67, ООО Ромашка, нужен насос для котельной"

Менеджер свяжется с вами в течение рабочего дня! 📧
        """
        
        # Возвращаемся к основной клавиатуре
        keyboard = get_main_reply_keyboard()
        
        await message.answer(contact_text, reply_markup=keyboard)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=contact_text
        )
        
        # Логируем запрос на связь
        await hybrid_logger.business(
            "Запрос связи с менеджером через кнопку",
            {"chat_id": message.chat.id, "username": message.from_user.username}
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_contact_button: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "❓ Помощь")
async def handle_help_button(message: Message, session: AsyncSession):
    """Обработчик кнопки Помощь"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем сообщение
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        help_text = """
<b>📖 Справка по использованию бота</b>

<b>🔍 Поиск товаров:</b>
Просто опишите, что ищете:
• "Нужен насос для воды"
• "Болты М12 оцинкованные"
• "Электродвигатель 3 кВт"

<b>💬 Консультации:</b>
Задавайте вопросы о:
• Технических характеристиках
• Совместимости оборудования
• Условиях поставки
• Ценах и наличии

<b>📞 Связь с менеджером:</b>
Используйте кнопку "📞 Связаться с менеджером" в меню

<b>⚡ Быстрые команды:</b>
/start - начать работу
/search - поиск товаров
/categories - категории товаров
/help - эта справка
/contact - связаться с менеджером

Я работаю 24/7 и отвечу в течение нескольких секунд! 🚀
        """
        
        # Возвращаемся к основной клавиатуре
        keyboard = get_main_reply_keyboard()
        
        await message.answer(help_text, reply_markup=keyboard)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=help_text
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_help_button: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "🏠 Главное меню")
async def handle_main_menu_button(message: Message, session: AsyncSession):
    """Обработчик кнопки Главное меню"""
    try:
        # Создаем или получаем пользователя
        await ensure_user_exists(
            session=session,
            chat_id=message.chat.id,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Сохраняем сообщение
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        welcome_text = f"""
👋 <b>Добро пожаловать!</b>

Я - AI-ассистент для консультации по каталогу товаров и услуг.

<b>Что я умею:</b>
• Поиск товаров по описанию
• Консультации по услугам компании  
• Помощь в выборе оборудования
• Связь с менеджерами

<b>Доступные команды:</b>
/help - справка по использованию
/contact - связаться с менеджером

Просто напишите, что вас интересует! 🔍
        """
        
        # Возвращаемся к основной клавиатуре
        keyboard = get_main_reply_keyboard()
        
        await message.answer(welcome_text, reply_markup=keyboard)
        
        # Сохраняем ответ
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=welcome_text
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_main_menu_button: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
