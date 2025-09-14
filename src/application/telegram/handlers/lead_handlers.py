"""
Обработчики для сбора контактных данных и создания лидов.
Согласно @vision.md - FSM для пошагового сбора с валидацией.
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from src.application.telegram.states.lead_states import LeadStates
from src.application.telegram.keyboards.lead_keyboards import (
    get_contact_manager_keyboard,
    get_contact_data_choice_keyboard,
    get_phone_request_keyboard,
    get_confirmation_keyboard,
    get_skip_optional_keyboard,
    get_edit_lead_keyboard
)
from src.application.telegram.services.lead_service import LeadService, LeadCreateRequest
from src.application.telegram.services.message_service import save_message
from src.infrastructure.logging.hybrid_logger import hybrid_logger
from src.infrastructure.database.models import User
from sqlalchemy import select


class LeadHandlers:
    """Класс обработчиков для работы с лидами"""
    
    def __init__(self, lead_service: LeadService) -> None:
        """Инициализация обработчиков лидов"""
        self.lead_service = lead_service
        self.router = Router()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Регистрируем handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Регистрация всех обработчиков"""
        
        # Добавляем обработчик help для совместимости с lead_keyboards
        self.router.callback_query.register(
            self.handle_help_callback,
            F.data == "help"
        )
        
        # Callback handlers
        self.router.callback_query.register(
            self.handle_contact_manager,
            F.data == "contact_manager"
        )
        self.router.callback_query.register(
            self.handle_quick_contact,
            F.data == "quick_contact"
        )
        self.router.callback_query.register(
            self.handle_full_contact_form,
            F.data == "full_contact_form"
        )
        self.router.callback_query.register(
            self.handle_share_phone,
            F.data == "share_phone"
        )
        self.router.callback_query.register(
            self.handle_enter_email,
            F.data == "enter_email"
        )
        self.router.callback_query.register(
            self.handle_use_telegram,
            F.data == "use_telegram"
        )
        self.router.callback_query.register(
            self.handle_skip_field,
            F.data == "skip_field"
        )
        self.router.callback_query.register(
            self.handle_skip_additional_contact,
            F.data == "skip_additional_contact"
        )
        self.router.callback_query.register(
            self.handle_confirm_lead,
            F.data == "confirm_lead"
        )
        self.router.callback_query.register(
            self.handle_edit_lead,
            F.data == "edit_lead"
        )
        self.router.callback_query.register(
            self.handle_cancel_contact,
            F.data.in_(["cancel_contact", "cancel_lead"])
        )
        
        # Message handlers для FSM состояний
        self.router.message.register(
            self.process_name_input,
            LeadStates.waiting_for_name
        )
        self.router.message.register(
            self.process_phone_input,
            LeadStates.waiting_for_phone
        )
        self.router.message.register(
            self.process_email_input,
            LeadStates.waiting_for_email
        )
        self.router.message.register(
            self.process_company_input,
            LeadStates.waiting_for_company
        )
        self.router.message.register(
            self.process_question_input,
            LeadStates.waiting_for_question
        )
        
        # Быстрый контакт
        self.router.message.register(
            self.process_quick_name,
            LeadStates.quick_contact_name
        )
        self.router.message.register(
            self.process_quick_phone,
            LeadStates.quick_contact_phone
        )
        self.router.message.register(
            self.process_quick_question,
            LeadStates.quick_contact_question
        )
    
    async def handle_contact_manager(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработчик кнопки 'Связаться с менеджером'"""
        try:
            await callback.message.edit_text(
                "📞 <b>Связь с менеджером</b>\n\n"
                "Выберите удобный способ:",
                reply_markup=get_contact_manager_keyboard()
            )
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_contact_manager: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")

    async def handle_help_callback(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработчик кнопки помощи в lead_keyboards"""
        try:
            await hybrid_logger.info(f"🔘 LeadHandlers.handle_help_callback вызван для пользователя {callback.from_user.id}")
            await callback.answer()
            
            # Вызываем базовую справку из basic_handlers
            from .basic_handlers import handle_help
            
            # Создаем фейковое сообщение для совместимости
            fake_message = type('obj', (object,), {
                'chat': callback.message.chat,
                'from_user': callback.from_user,
                'text': '/help',
                'answer': callback.message.edit_text
            })
            
            await handle_help(fake_message, session)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_help_callback: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def handle_quick_contact(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Быстрый сбор контактов"""
        try:
            await callback.message.edit_text(
                "⚡ <b>Быстрый контакт</b>\n\n"
                "Укажите ваше имя:",
                reply_markup=None
            )
            await state.set_state(LeadStates.quick_contact_name)
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_quick_contact: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def handle_full_contact_form(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Полная форма сбора контактов"""
        try:
            await callback.message.edit_text(
                "📝 <b>Подробная заявка</b>\n\n"
                "Для начала укажите ваше имя:",
                reply_markup=None
            )
            await state.set_state(LeadStates.waiting_for_name)
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_full_contact_form: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def process_name_input(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка ввода имени"""
        try:
            name = message.text.strip()
            if len(name) < 1:
                await message.answer("❌ Имя не может быть пустым. Попробуйте еще раз:")
                return
            
            if len(name) > 200:
                await message.answer("❌ Имя слишком длинное (максимум 200 символов). Попробуйте еще раз:")
                return
            
            # Сохраняем в состоянии
            await state.update_data(name=name)
            
            await message.answer(
                f"👤 Имя: <b>{name}</b>\n\n"
                "📱 Теперь укажите способ связи:",
                reply_markup=get_contact_data_choice_keyboard()
            )
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_name_input: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def handle_share_phone(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка выбора 'Поделиться телефоном'"""
        try:
            await callback.message.edit_text(
                "📱 <b>Номер телефона</b>\n\n"
                "Поделитесь номером телефона или введите вручную:",
                reply_markup=None
            )
            
            await callback.message.answer(
                "Выберите способ:",
                reply_markup=get_phone_request_keyboard()
            )
            
            await state.set_state(LeadStates.waiting_for_phone)
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_share_phone: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def process_phone_input(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка ввода телефона"""
        try:
            # Убираем клавиатуру
            await message.answer(".", reply_markup=ReplyKeyboardRemove())
            
            phone = None
            
            # Обработка контакта
            if message.contact:
                phone = message.contact.phone_number
                if not phone.startswith('+'):
                    phone = '+' + phone
            
            # Обработка текста
            elif message.text:
                if message.text == "❌ Отмена":
                    await self._cancel_form(message, state)
                    return
                elif message.text == "⏭ Ввести вручную":
                    await message.answer("Введите номер телефона в международном формате (+7...):")
                    return
                else:
                    phone = message.text.strip()
            
            if not phone:
                await message.answer("❌ Некорректный телефон. Попробуйте еще раз:")
                return
            
            # Валидация через LeadCreateRequest
            try:
                # Создаем временный объект для валидации
                temp_data = LeadCreateRequest(name="temp", phone=phone)
                validated_phone = temp_data.phone
                
                # Сохраняем валидированный телефон
                await state.update_data(phone=validated_phone)
                
                await message.answer(
                    f"📱 Телефон: <b>{validated_phone}</b>\n\n"
                    "📧 Хотите также указать email? (необязательно)",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.waiting_for_email)
                
            except ValidationError as ve:
                error_msg = "❌ Некорректный формат телефона.\n"
                for error in ve.errors():
                    error_msg += f"• {error['msg']}\n"
                error_msg += "\nПопробуйте еще раз:"
                await message.answer(error_msg)
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_phone_input: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def handle_enter_email(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка выбора 'Ввести email'"""
        try:
            await callback.message.edit_text(
                "📧 <b>Email адрес</b>\n\n"
                "Введите ваш email адрес:",
                reply_markup=get_skip_optional_keyboard()
            )
            await state.set_state(LeadStates.waiting_for_email)
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_enter_email: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def process_email_input(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка ввода email"""
        try:
            email = message.text.strip()
            
            # Валидация email
            try:
                temp_data = LeadCreateRequest(name="temp", email=email)
                validated_email = str(temp_data.email)
                
                await state.update_data(email=validated_email)
                
                await message.answer(
                    f"📧 Email: <b>{validated_email}</b>\n\n"
                    "🏢 Укажите название компании (необязательно):",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.waiting_for_company)
                
            except ValidationError:
                await message.answer("❌ Некорректный email адрес. Попробуйте еще раз:")
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_email_input: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def handle_use_telegram(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Использование Telegram как контакта"""
        try:
            # Получаем username пользователя
            telegram_username = callback.from_user.username
            if telegram_username:
                telegram_contact = f"@{telegram_username}"
                await state.update_data(telegram=telegram_contact)
                
                await callback.message.edit_text(
                    f"💬 Telegram: <b>{telegram_contact}</b>\n\n"
                    "🏢 Укажите название компании (необязательно):",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.waiting_for_company)
            else:
                await callback.message.edit_text(
                    "❌ У вас не установлен username в Telegram.\n"
                    "Выберите другой способ связи:",
                    reply_markup=get_contact_data_choice_keyboard()
                )
            
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_use_telegram: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def handle_skip_field(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Пропуск опционального поля"""
        try:
            current_state = await state.get_state()
            
            if current_state == LeadStates.waiting_for_email.state:
                await callback.message.edit_text(
                    "🏢 Укажите название компании (необязательно):",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.waiting_for_company)
                
            elif current_state == LeadStates.waiting_for_company.state:
                await callback.message.edit_text(
                    "❓ Опишите ваш вопрос или потребность (необязательно):",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.waiting_for_question)
                
            elif current_state == LeadStates.waiting_for_question.state:
                await self._show_confirmation(callback.message, state)
            
            await callback.answer()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_skip_field: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")

    async def handle_skip_additional_contact(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Пропуск дополнительного контакта"""
        try:
            await callback.answer()
            
            # Переходим к следующему обязательному полю или показываем подтверждение
            current_state = await state.get_state()
            
            if current_state == LeadStates.waiting_for_phone.state:
                # Если пропускаем телефон, переходим к email
                await callback.message.edit_text(
                    "📧 Укажите email для связи (необязательно):",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.waiting_for_email)
            else:
                # Показываем подтверждение с имеющимися данными
                await self._show_confirmation(callback.message, state)
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_skip_additional_contact: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def process_company_input(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка ввода названия компании"""
        try:
            company = message.text.strip()
            
            if len(company) > 300:
                await message.answer("❌ Название компании слишком длинное (максимум 300 символов). Попробуйте еще раз:")
                return
            
            await state.update_data(company=company)
            
            await message.answer(
                f"🏢 Компания: <b>{company}</b>\n\n"
                "❓ Опишите ваш вопрос или потребность (необязательно):",
                reply_markup=get_skip_optional_keyboard()
            )
            await state.set_state(LeadStates.waiting_for_question)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_company_input: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def process_question_input(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка ввода вопроса"""
        try:
            question = message.text.strip()
            await state.update_data(question=question)
            await self._show_confirmation(message, state)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_question_input: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def _show_confirmation(self, message: Message, state: FSMContext) -> None:
        """Показ подтверждения данных"""
        try:
            data = await state.get_data()
            
            confirmation_text = "📋 <b>Проверьте данные:</b>\n\n"
            confirmation_text += f"👤 <b>Имя:</b> {data.get('name', '—')}\n"
            
            if data.get('phone'):
                confirmation_text += f"📱 <b>Телефон:</b> {data['phone']}\n"
            if data.get('email'):
                confirmation_text += f"📧 <b>Email:</b> {data['email']}\n"
            if data.get('telegram'):
                confirmation_text += f"💬 <b>Telegram:</b> {data['telegram']}\n"
            if data.get('company'):
                confirmation_text += f"🏢 <b>Компания:</b> {data['company']}\n"
            if data.get('question'):
                confirmation_text += f"❓ <b>Вопрос:</b> {data['question']}\n"
            
            confirmation_text += "\n✅ Все верно?"
            
            await message.answer(
                confirmation_text,
                reply_markup=get_confirmation_keyboard()
            )
            await state.set_state(LeadStates.confirming_lead)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в _show_confirmation: {e}")
            await message.answer("Произошла ошибка при формировании подтверждения.")
    
    async def handle_confirm_lead(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Подтверждение и создание лида"""
        try:
            data = await state.get_data()
            
            # Получаем user_id
            user_query = select(User).where(User.chat_id == callback.message.chat.id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                await callback.answer("❌ Ошибка: пользователь не найден")
                return
            
            # Создаем лид
            lead_data = LeadCreateRequest(
                name=data['name'],
                phone=data.get('phone'),
                email=data.get('email'),
                telegram=data.get('telegram'),
                company=data.get('company'),
                question=data.get('question'),
                auto_created=False
            )
            
            lead = await self.lead_service.create_lead(session, user.id, lead_data)
            
            await callback.message.edit_text(
                "✅ <b>Заявка успешно отправлена!</b>\n\n"
                "📞 Менеджер свяжется с вами в ближайшее время.\n"
                f"📋 Номер заявки: <code>{lead.id}</code>\n\n"
                "Спасибо за обращение! 🙏",
                reply_markup=None
            )
            
            # Отправляем уведомление менеджерам
            await self._notify_managers(session, lead, callback.message.chat.id)
            
            await state.clear()
            await callback.answer("Заявка отправлена!")
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_confirm_lead: {e}")
            await callback.answer("❌ Ошибка при создании заявки")
            await callback.message.edit_text(
                "❌ Произошла ошибка при отправке заявки.\n"
                "Попробуйте позже или свяжитесь с нами другим способом.",
                reply_markup=None
            )

    async def handle_edit_lead(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Редактирование данных лида"""
        try:
            await callback.answer()
            
            # Показываем меню редактирования
            user_data = await state.get_data()
            name = user_data.get('name', 'Не указано')
            phone = user_data.get('phone', 'Не указано')
            email = user_data.get('email', 'Не указано')
            company = user_data.get('company', 'Не указано')
            question = user_data.get('question', 'Не указано')
            
            edit_text = (
                "✏️ <b>Редактирование заявки</b>\n\n"
                f"👤 <b>Имя:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}\n"
                f"📧 <b>Email:</b> {email}\n"
                f"🏢 <b>Компания:</b> {company}\n"
                f"❓ <b>Вопрос:</b> {question}\n\n"
                "Редактирование отдельных полей будет доступно в следующих итерациях.\n"
                "Сейчас можете заполнить заново или подтвердить текущие данные."
            )
            
            await callback.message.edit_text(
                edit_text,
                parse_mode="HTML",
                reply_markup=get_confirmation_keyboard()
            )
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_edit_lead: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    
    async def handle_cancel_contact(
        self, 
        callback: CallbackQuery, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Отмена процесса создания лида"""
        try:
            await state.clear()
            await callback.message.edit_text(
                "❌ Создание заявки отменено.\n\n"
                "Если понадобится помощь - обращайтесь! 😊",
                reply_markup=None
            )
            await callback.answer("Отменено")
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в handle_cancel_contact: {e}")
            await callback.answer("Произошла ошибка")
    
    # Быстрый контакт handlers
    async def process_quick_name(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка имени в быстром контакте"""
        try:
            name = message.text.strip()
            if len(name) < 1 or len(name) > 200:
                await message.answer("❌ Некорректное имя. Попробуйте еще раз:")
                return
            
            await state.update_data(name=name)
            await message.answer(
                f"👤 Имя: <b>{name}</b>\n\n"
                "📱 Введите номер телефона:",
                reply_markup=get_phone_request_keyboard()
            )
            await state.set_state(LeadStates.quick_contact_phone)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_quick_name: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def process_quick_phone(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка телефона в быстром контакте"""
        try:
            # Аналогично process_phone_input, но переходим к вопросу
            await message.answer(".", reply_markup=ReplyKeyboardRemove())
            
            phone = None
            if message.contact:
                phone = message.contact.phone_number
                if not phone.startswith('+'):
                    phone = '+' + phone
            elif message.text and message.text not in ["❌ Отмена", "⏭ Ввести вручную"]:
                phone = message.text.strip()
            
            if message.text == "❌ Отмена":
                await self._cancel_form(message, state)
                return
            elif message.text == "⏭ Ввести вручную":
                await message.answer("Введите номер телефона в международном формате:")
                return
            
            if not phone:
                await message.answer("❌ Некорректный телефон. Попробуйте еще раз:")
                return
            
            try:
                temp_data = LeadCreateRequest(name="temp", phone=phone)
                validated_phone = temp_data.phone
                
                await state.update_data(phone=validated_phone)
                await message.answer(
                    f"📱 Телефон: <b>{validated_phone}</b>\n\n"
                    "❓ Кратко опишите ваш вопрос:",
                    reply_markup=get_skip_optional_keyboard()
                )
                await state.set_state(LeadStates.quick_contact_question)
                
            except ValidationError as ve:
                error_msg = "❌ Некорректный формат телефона. Попробуйте еще раз:"
                await message.answer(error_msg)
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_quick_phone: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")
    
    async def process_quick_question(
        self, 
        message: Message, 
        state: FSMContext,
        session: AsyncSession
    ) -> None:
        """Обработка вопроса в быстром контакте"""
        try:
            question = message.text.strip()
            await state.update_data(question=question)
            
            # Сразу создаем лид
            data = await state.get_data()
            
            # Получаем user_id
            user_query = select(User).where(User.chat_id == message.chat.id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                await message.answer("❌ Ошибка: пользователь не найден")
                return
            
            # Автоматически добавляем Telegram username если есть
            telegram_contact = None
            if message.from_user.username:
                telegram_contact = f"@{message.from_user.username}"
            
            lead_data = LeadCreateRequest(
                name=data['name'],
                phone=data.get('phone'),
                telegram=telegram_contact,
                question=question,
                auto_created=False
            )
            
            lead = await self.lead_service.create_lead(session, user.id, lead_data)
            
            await message.answer(
                "✅ <b>Заявка отправлена!</b>\n\n"
                "📞 Менеджер свяжется с вами в ближайшее время.\n"
                f"📋 Номер заявки: <code>{lead.id}</code>",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Уведомляем менеджеров
            await self._notify_managers(session, lead, message.chat.id)
            
            await state.clear()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка в process_quick_question: {e}")
            await message.answer("❌ Произошла ошибка при отправке заявки.")
    
    async def _cancel_form(self, message: Message, state: FSMContext) -> None:
        """Отмена формы"""
        await state.clear()
        await message.answer(
            "❌ Создание заявки отменено.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def _notify_managers(self, session: AsyncSession, lead, chat_id: int) -> None:
        """Уведомление менеджеров о новом лиде"""
        try:
            # Получаем экземпляр бота из контекста
            from aiogram import Bot
            from src.config.settings import settings
            from src.infrastructure.notifications.telegram_notifier import get_telegram_notifier
            
            bot = Bot(token=settings.bot_token)
            notifier = get_telegram_notifier(bot)
            
            # Отправляем уведомление
            success = await notifier.notify_new_lead(lead, chat_id)
            
            if success:
                await hybrid_logger.business(
                    "Уведомление о лиде отправлено менеджерам",
                    {
                        "lead_id": lead.id,
                        "chat_id": chat_id,
                        "auto_created": lead.auto_created
                    }
                )
            else:
                await hybrid_logger.warning(
                    "Не удалось отправить уведомление менеджерам",
                    {"lead_id": lead.id}
                )
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка уведомления менеджеров: {e}")
