"""
Unit тесты для валидации лидов
"""
import pytest
from pydantic import ValidationError

from src.application.telegram.services.lead_service import LeadCreateRequest
from src.domain.entities.lead import LeadSource


class TestLeadValidation:
    """Тесты валидации данных лидов"""
    
    def test_valid_lead_creation(self):
        """Тест создания валидного лида"""
        lead_data = LeadCreateRequest(
            name="Иван Петров",
            phone="+79001234567",
            email="ivan@example.com",
            telegram="@ivan_user",
            company="ООО Тест",
            question="Нужен насос для дома"
        )
        
        assert lead_data.name == "Иван Петров"
        assert lead_data.phone == "+79001234567"
        assert lead_data.email == "ivan@example.com"
        assert lead_data.telegram == "@ivan_user"
        assert lead_data.has_contact() is True
    
    def test_phone_validation_russian_formats(self):
        """Тест валидации российских номеров в разных форматах"""
        # Валидные форматы
        valid_phones = [
            "+79001234567",     # Стандартный международный
            "89001234567",      # С 8
            "79001234567",      # Без + и 8
            "+7 900 123 45 67", # С пробелами
            "+7(900)123-45-67", # С разделителями
        ]
        
        for phone in valid_phones:
            lead = LeadCreateRequest(
                name="Тест", 
                phone=phone,
                lead_source=LeadSource.TELEGRAM_BOT
            )
            assert lead.phone == "+79001234567"
    
    def test_phone_validation_international(self):
        """Тест валидации международных номеров"""
        valid_international = [
            "+1234567890",      # США (10 цифр)
            "+491234567890",    # Германия (11 цифр)
            "+861234567890123", # Китай (13 цифр)
        ]
        
        for phone in valid_international:
            lead = LeadCreateRequest(
                name="Тест",
                phone=phone,
                lead_source=LeadSource.TELEGRAM_BOT
            )
            assert lead.phone == phone
    
    def test_phone_validation_invalid_formats(self):
        """Тест невалидных форматов телефонов"""
        invalid_phones = [
            "123",              # Слишком короткий
            "+712345",          # Российский слишком короткий
            "+7123456789012",   # Российский слишком длинный
            "абвгд",           # Не цифры
            "+0123456789",      # Начинается с 0
            "++79001234567",    # Двойной +
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                LeadCreateRequest(
                    name="Тест",
                    phone=phone,
                    lead_source=LeadSource.TELEGRAM_BOT
                )
    
    def test_telegram_username_validation(self):
        """Тест валидации Telegram username"""
        # Валидные варианты
        valid_usernames = [
            "@valid_user123",
            "valid_user123",    # Без @
            "@user_with_underscores",
        ]
        
        for username in valid_usernames:
            lead = LeadCreateRequest(
                name="Тест",
                telegram=username,
                lead_source=LeadSource.TELEGRAM_BOT
            )
            assert lead.telegram.startswith("@")
    
    def test_telegram_username_invalid(self):
        """Тест невалидных Telegram username"""
        invalid_usernames = [
            "@abc",             # Слишком короткий (< 5 символов)
            "@user-with-dash",  # Дефис запрещен  
            "@user.with.dots",  # Точки запрещены
            "@" + "a" * 33,     # Слишком длинный (> 32 символов)
            "@",                # Только @
            "ab",               # Слишком короткий без @
        ]
        
        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                LeadCreateRequest(
                    name="Тест",
                    telegram=username,
                    lead_source=LeadSource.TELEGRAM_BOT
                )
    
    def test_email_validation(self):
        """Тест валидации email"""
        # Валидные email
        valid_emails = [
            "test@example.com",
            "user.name@domain.ru",
            "user+tag@example.org",
        ]
        
        for email in valid_emails:
            lead = LeadCreateRequest(
                name="Тест",
                email=email,
                lead_source=LeadSource.TELEGRAM_BOT
            )
            assert lead.email == email
        
        # Невалидные email
        invalid_emails = [
            "notanemail",
            "@domain.com",
            "user@",
            "user@domain",
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                LeadCreateRequest(
                    name="Тест",
                    email=email,
                    lead_source=LeadSource.TELEGRAM_BOT
                )
    
    def test_name_validation(self):
        """Тест валидации имени"""
        # Валидные имена
        valid_names = [
            "А",                # Минимум 1 символ
            "Иван Петров",      # Стандартное имя
            "А" * 200,          # Максимум 200 символов
        ]
        
        for name in valid_names:
            lead = LeadCreateRequest(
                name=name,
                phone="+79001234567",
                lead_source=LeadSource.TELEGRAM_BOT
            )
            assert lead.name == name
        
        # Невалидные имена
        with pytest.raises(ValidationError):
            LeadCreateRequest(
                name="",           # Пустое имя
                phone="+79001234567",
                lead_source=LeadSource.TELEGRAM_BOT
            )
        
        with pytest.raises(ValidationError):
            LeadCreateRequest(
                name="А" * 201,    # Слишком длинное имя
                phone="+79001234567", 
                lead_source=LeadSource.TELEGRAM_BOT
            )
    
    def test_contact_requirement(self):
        """Тест требования наличия контактов"""
        # Лид должен иметь хотя бы один контакт
        
        # С телефоном - OK
        lead_with_phone = LeadCreateRequest(
            name="Тест",
            phone="+79001234567",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead_with_phone.has_contact() is True
        
        # С email - OK  
        lead_with_email = LeadCreateRequest(
            name="Тест",
            email="test@example.com",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead_with_email.has_contact() is True
        
        # С telegram - OK
        lead_with_telegram = LeadCreateRequest(
            name="Тест",
            telegram="@test_user",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead_with_telegram.has_contact() is True
        
        # Без контактов - FAIL
        lead_no_contacts = LeadCreateRequest(
            name="Тест",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead_no_contacts.has_contact() is False
    
    def test_lead_source_enum(self):
        """Тест работы с enum источника лида"""
        # Все доступные источники
        sources = [
            LeadSource.TELEGRAM_BOT,
            LeadSource.WEBSITE_WIDGET,
        ]
        
        for source in sources:
            lead = LeadCreateRequest(
                name="Тест",
                phone="+79001234567",
                lead_source=source
            )
            # Enum остается enum'ом (без use_enum_values)
            assert lead.lead_source == source
    
    def test_auto_created_flag(self):
        """Тест флага автоматического создания"""
        # По умолчанию не автосозданный
        lead_manual = LeadCreateRequest(
            name="Тест",
            phone="+79001234567",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead_manual.auto_created is False
        
        # Автосозданный
        lead_auto = LeadCreateRequest(
            name="Тест",
            phone="+79001234567",
            auto_created=True,
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead_auto.auto_created is True
    
    def test_company_validation(self):
        """Тест валидации названия компании"""
        # Валидная компания
        lead = LeadCreateRequest(
            name="Тест",
            phone="+79001234567",
            company="ООО Рога и Копыта",
            lead_source=LeadSource.TELEGRAM_BOT
        )
        assert lead.company == "ООО Рога и Копыта"
        
        # Слишком длинная компания
        with pytest.raises(ValidationError):
            LeadCreateRequest(
                name="Тест",
                phone="+79001234567",
                company="А" * 301,  # Максимум 300 символов
                lead_source=LeadSource.TELEGRAM_BOT
            )
