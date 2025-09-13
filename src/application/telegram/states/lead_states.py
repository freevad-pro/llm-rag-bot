"""
FSM состояния для сбора контактных данных лидов.
Согласно @vision.md - пошаговый сбор с валидацией.
"""
from aiogram.fsm.state import State, StatesGroup


class LeadStates(StatesGroup):
    """Состояния для процесса сбора контактов лида"""
    
    # Сбор основных данных
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_company = State()
    waiting_for_question = State()
    
    # Подтверждение
    confirming_lead = State()
    
    # Состояния для быстрого контакта
    quick_contact_name = State()
    quick_contact_phone = State()
    quick_contact_question = State()
