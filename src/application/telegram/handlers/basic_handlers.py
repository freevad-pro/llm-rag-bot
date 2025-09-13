"""
Базовые обработчики команд для Telegram бота
Реализует /start, /help, /contact согласно @vision.md
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.application.telegram.services.user_service import ensure_user_exists
from src.application.telegram.services.message_service import save_message


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
        
        # Inline клавиатура с быстрыми действиями
        from src.application.telegram.keyboards.lead_keyboards import get_main_menu_keyboard
        keyboard = get_main_menu_keyboard()
        
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
        
        await hybrid_logger.business(
            f"Новый пользователь: {user.chat_id}",
            {"username": user.username, "first_name": user.first_name}
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(Command("help"))
async def handle_help(message: Message, session: AsyncSession):
    """Обработчик команды /help"""
    try:
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


@router.message(F.text)
async def handle_text_message(message: Message, session: AsyncSession):
    """Обработчик текстовых сообщений"""
    try:
        # Сохраняем сообщение пользователя
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="user",
            content=message.text
        )
        
        # Пока что простой ответ (в Итерации 4 здесь будет LLM)
        response_text = """
Спасибо за ваше сообщение! 

В данный момент я нахожусь в базовой версии. 
Полноценная обработка запросов будет реализована в следующих итерациях.

Для срочных вопросов используйте команду /contact для связи с менеджером.
        """
        
        sent_message = await message.answer(response_text)
        
        # Сохраняем ответ бота
        await save_message(
            session=session,
            chat_id=message.chat.id,
            role="assistant",
            content=response_text
        )
        
        await hybrid_logger.business(
            "Обработка текстового сообщения",
            {"chat_id": message.chat.id, "message_length": len(message.text)}
        )
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в handle_text_message: {e}")
        await message.answer("Произошла ошибка при обработке сообщения.")


# Обработчик callback запросов от inline кнопок
@router.callback_query(F.data == "help")
async def callback_help(callback_query, session: AsyncSession):
    """Обработчик callback для кнопки помощи"""
    await callback_query.answer()
    
    # Вызываем обработчик help через имитацию команды
    fake_message = type('obj', (object,), {
        'chat': callback_query.message.chat,
        'from_user': callback_query.from_user,
        'text': '/help'
    })
    
    await handle_help(fake_message, session)


@router.callback_query(F.data == "contact_manager")
async def callback_contact(callback_query, session: AsyncSession):
    """Обработчик callback для кнопки связи с менеджером"""
    await callback_query.answer("Переключаю на связь с менеджером...")
    
    # Вызываем обработчик contact
    fake_message = type('obj', (object,), {
        'chat': callback_query.message.chat,
        'from_user': callback_query.from_user,
        'text': '/contact'
    })
    
    await handle_contact(fake_message, session)
