"""
Клавиатуры для работы с лидами.
Согласно @vision.md - inline кнопки для навигации.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_contact_manager_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для связи с менеджером"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📞 Быстрый контакт", 
                callback_data="quick_contact"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Подробная заявка", 
                callback_data="full_contact_form"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена", 
                callback_data="cancel_contact"
            )
        ]
    ])


def get_contact_data_choice_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа предоставления контактов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Поделиться телефоном", 
                callback_data="share_phone"
            )
        ],
        [
            InlineKeyboardButton(
                text="📧 Ввести email", 
                callback_data="enter_email"
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Связаться через Telegram", 
                callback_data="use_telegram"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏭ Пропустить", 
                callback_data="skip_additional_contact"
            )
        ]
    ])


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса телефона"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Поделиться номером телефона",
                    request_contact=True
                )
            ],
            [
                KeyboardButton(text="⏭ Ввести вручную")
            ],
            [
                KeyboardButton(text="❌ Отмена")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения создания лида"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Отправить заявку", 
                callback_data="confirm_lead"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Исправить данные", 
                callback_data="edit_lead"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена", 
                callback_data="cancel_lead"
            )
        ]
    ])


def get_skip_optional_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пропуска опциональных полей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⏭ Пропустить", 
                callback_data="skip_field"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена", 
                callback_data="cancel_contact"
            )
        ]
    ])


def get_edit_lead_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для редактирования данных лида"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Изменить имя", callback_data="edit_name"),
            InlineKeyboardButton(text="📱 Изменить телефон", callback_data="edit_phone")
        ],
        [
            InlineKeyboardButton(text="📧 Изменить email", callback_data="edit_email"),
            InlineKeyboardButton(text="🏢 Изменить компанию", callback_data="edit_company")
        ],
        [
            InlineKeyboardButton(text="❓ Изменить вопрос", callback_data="edit_question")
        ],
        [
            InlineKeyboardButton(text="✅ Готово", callback_data="confirm_lead")
        ]
    ])


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Основная клавиатура с добавленной кнопкой связи с менеджером"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Поиск товаров", callback_data="new_search")
        ],
        [
            InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="contact_manager"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])
