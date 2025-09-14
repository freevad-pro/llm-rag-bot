"""
Сервис управления лидами.
Согласно @vision.md - создание, валидация, автоматическое создание при неактивности.
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.sql import func

from src.infrastructure.database.models import Lead as LeadModel, User, Conversation
from src.domain.entities.lead import Lead, LeadStatus, LeadSource
from src.infrastructure.logging.hybrid_logger import hybrid_logger


class LeadCreateRequest(BaseModel):
    """Модель для создания лида с валидацией"""
    name: str = Field(min_length=1, max_length=200, description="Имя клиента")
    phone: Optional[str] = Field(None, description="Телефон в международном формате")
    email: Optional[EmailStr] = Field(None, description="Email адрес")
    telegram: Optional[str] = Field(None, max_length=255, description="Telegram username")
    company: Optional[str] = Field(None, max_length=300, description="Название компании")
    question: Optional[str] = Field(None, description="Вопрос или потребность")
    auto_created: bool = Field(False, description="Создан автоматически")
    lead_source: LeadSource = Field(LeadSource.TELEGRAM_BOT, description="Источник лида")

    @validator('phone')
    def validate_phone(cls, v):
        """
        Улучшенная валидация телефона для российских и международных номеров.
        Поддерживает форматы:
        - Российские: +7XXXXXXXXXX, 8XXXXXXXXXX, 7XXXXXXXXXX
        - Международные: +[1-9]XXXXXXX (7-15 цифр общей длины)
        """
        if v is None:
            return v
        
        original_input = v
        
        # Удаляем все символы кроме цифр и +
        phone_clean = re.sub(r'[^\d+]', '', v)
        
        # Проверяем что остались только цифры и плюс
        if not phone_clean or phone_clean == '+':
            raise ValueError('Некорректный телефон. Введите номер в международном формате.')
        
        # Убираем лишние плюсы
        if phone_clean.count('+') > 1:
            raise ValueError('Некорректный формат телефона.')
        
        # Обрабатываем российские номера
        if phone_clean.startswith('8') and len(phone_clean) == 11:
            # 89001234567 → +79001234567
            phone_clean = '+7' + phone_clean[1:]
        elif phone_clean.startswith('7') and len(phone_clean) == 11 and not phone_clean.startswith('+'):
            # 79001234567 → +79001234567
            phone_clean = '+' + phone_clean
        elif not phone_clean.startswith('+'):
            # Добавляем + для международных номеров
            phone_clean = '+' + phone_clean
        
        # Проверяем формат международного номера
        # +[1-9] за которым следует 6-14 цифр (общая длина 7-15)
        if not re.match(r'^\+[1-9]\d{6,14}$', phone_clean):
            raise ValueError(
                'Некорректный формат телефона. '
                'Используйте международный формат: +7XXXXXXXXXX или +1XXXXXXXXX'
            )
        
        # Дополнительная проверка для российских номеров
        if phone_clean.startswith('+7'):
            if len(phone_clean) != 12:  # +7 + 10 цифр
                raise ValueError('Российский номер должен содержать 10 цифр после +7')
            
            # Проверяем что код оператора корректный (9XX, 8XX, 3XX, 4XX, 5XX, 6XX)
            operator_code = phone_clean[2:5]
            if not re.match(r'^[3-9]\d{2}$', operator_code):
                raise ValueError('Некорректный код оператора для российского номера')
        
        return phone_clean

    @validator('telegram')
    def validate_telegram(cls, v):
        """Валидация Telegram username"""
        if v is None:
            return v
        
        # Убираем @ в начале если есть
        username = v.lstrip('@')
        
        # Проверяем формат username
        if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
            raise ValueError('Некорректный Telegram username')
        
        return '@' + username

    def has_contact(self) -> bool:
        """Проверка наличия контактных данных"""
        return bool(self.phone or self.email or self.telegram)

    class Config:
        """Конфигурация Pydantic модели"""
        use_enum_values = True


class LeadService:
    """Сервис для управления лидами"""
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    async def create_lead(
        self,
        session: AsyncSession,
        user_id: int,
        lead_data: LeadCreateRequest
    ) -> Lead:
        """
        Создание нового лида с валидацией.
        
        Args:
            session: Сессия БД
            user_id: ID пользователя
            lead_data: Валидированные данные лида
            
        Returns:
            Созданный лид
            
        Raises:
            ValueError: При невалидных данных
        """
        try:
            # Дополнительная валидация
            if not lead_data.has_contact():
                raise ValueError("Необходимо указать минимум один контакт: телефон, email или Telegram")
            
            # Создаем модель БД
            lead_model = LeadModel(
                user_id=user_id,
                name=lead_data.name.strip(),
                phone=lead_data.phone,
                email=str(lead_data.email) if lead_data.email else None,
                telegram=lead_data.telegram,
                company=lead_data.company.strip() if lead_data.company else None,
                question=lead_data.question.strip() if lead_data.question else None,
                auto_created=lead_data.auto_created,
                lead_source=lead_data.lead_source.value,
                status=LeadStatus.PENDING_SYNC.value
            )
            
            session.add(lead_model)
            await session.commit()
            await session.refresh(lead_model)
            
            # Конвертируем в domain сущность
            lead = self._model_to_entity(lead_model)
            
            await hybrid_logger.business(
                "Лид создан",
                {
                    "lead_id": lead.id,
                    "user_id": user_id,
                    "auto_created": lead_data.auto_created,
                    "has_phone": bool(lead_data.phone),
                    "has_email": bool(lead_data.email),
                    "has_telegram": bool(lead_data.telegram)
                }
            )
            
            return lead
            
        except Exception as e:
            await session.rollback()
            await hybrid_logger.error(f"Ошибка создания лида: {e}")
            raise
    
    async def get_user_leads(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[Lead]:
        """Получение лидов пользователя"""
        try:
            query = select(LeadModel).where(
                LeadModel.user_id == user_id
            ).order_by(LeadModel.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            lead_models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in lead_models]
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка получения лидов пользователя {user_id}: {e}")
            raise
    
    async def check_recent_lead(
        self,
        session: AsyncSession,
        user_id: int,
        hours: int = 24
    ) -> Optional[Lead]:
        """Проверка наличия недавнего лида"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = select(LeadModel).where(
                and_(
                    LeadModel.user_id == user_id,
                    LeadModel.created_at >= since
                )
            ).order_by(LeadModel.created_at.desc())
            
            result = await session.execute(query)
            lead_model = result.scalars().first()
            
            return self._model_to_entity(lead_model) if lead_model else None
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка проверки недавнего лида: {e}")
            return None
    
    async def find_inactive_users(
        self,
        session: AsyncSession,
        inactive_minutes: int = 30
    ) -> List[tuple[int, datetime]]:
        """
        Поиск неактивных пользователей для автоматического создания лидов.
        
        Returns:
            List[(user_id, last_activity)]
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=inactive_minutes)
            
            # Последняя активность из сообщений
            subquery = select(
                Conversation.user_id,
                func.max(Conversation.started_at).label('last_activity')
            ).where(
                Conversation.started_at >= cutoff_time - timedelta(hours=24)  # В последние 24 часа
            ).group_by(Conversation.user_id).subquery()
            
            # Пользователи без недавних лидов  
            # Простая логика: проверяем есть ли недавние лиды для пользователя
            query = select(
                subquery.c.user_id,
                subquery.c.last_activity
            ).where(
                and_(
                    subquery.c.last_activity <= cutoff_time,
                    # Проверяем что нет недавних лидов для этого user_id
                    ~select(LeadModel.id).where(
                        and_(
                            LeadModel.user_id == subquery.c.user_id,
                            LeadModel.created_at >= cutoff_time
                        )
                    ).exists()
                )
            )
            
            result = await session.execute(query)
            return result.all()
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка поиска неактивных пользователей: {e}")
            return []
    
    async def auto_create_lead_for_user(
        self,
        session: AsyncSession,
        user_id: int
    ) -> Optional[Lead]:
        """Автоматическое создание лида для неактивного пользователя"""
        try:
            # Получаем данные пользователя
            user_query = select(User).where(User.id == user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
                
            # Дополнительная проверка: есть ли уже лид для этого telegram_user_id
            # Это предотвращает дубликаты при перезапуске бота
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(minutes=30)
            
            existing_lead_query = select(LeadModel.id).select_from(
                LeadModel.join(User, User.id == LeadModel.user_id)
            ).where(
                and_(
                    User.telegram_user_id == user.telegram_user_id,
                    LeadModel.created_at >= cutoff_time
                )
            )
            existing_result = await session.execute(existing_lead_query)
            if existing_result.scalar_one_or_none():
                # Уже есть недавний лид для этого telegram пользователя
                return None
            
            # Определяем имя
            name = None
            if user.first_name:
                name = user.first_name
                if user.last_name:
                    name += f" {user.last_name}"
            elif user.last_name:
                name = user.last_name
            elif user.username:
                name = user.username
            else:
                # Не можем создать лид без имени
                return None
            
            # Подготавливаем данные лида
            lead_data = LeadCreateRequest(
                name=name,
                phone=user.phone,
                email=user.email,
                telegram=f"@{user.username}" if user.username else None,
                auto_created=True,
                question="Автоматически создан при завершении диалога"
            )
            
            # Проверяем наличие контактов
            if not lead_data.has_contact():
                # Добавляем Telegram ID как контакт
                lead_data.telegram = f"tg://user?id={user.telegram_user_id}"
            
            return await self.create_lead(session, user_id, lead_data)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка автосоздания лида для пользователя {user_id}: {e}")
            return None
    
    def _model_to_entity(self, model: LeadModel) -> Lead:
        """Конвертация модели БД в domain сущность"""
        return Lead(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            phone=model.phone,
            email=model.email,
            telegram=model.telegram,
            company=model.company,
            question=model.question,
            status=LeadStatus(model.status),
            sync_attempts=model.sync_attempts,
            zoho_lead_id=model.zoho_lead_id,
            last_sync_attempt=model.last_sync_attempt,
            auto_created=model.auto_created,
            lead_source=LeadSource(model.lead_source),
            created_at=model.created_at
        )
