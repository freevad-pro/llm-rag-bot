"""
Сущности для статистики использования AI токенов
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal


class UsageStatisticsBase(BaseModel):
    """Базовая модель статистики использования"""
    provider: str = Field(..., description="AI провайдер (openai, yandexgpt)")
    model: str = Field(..., description="Модель AI (gpt-4o-mini, gpt-4o, yandexgpt-lite)")
    year: int = Field(..., description="Год")
    month: int = Field(..., ge=1, le=12, description="Месяц (1-12)")
    total_tokens: int = Field(default=0, description="Общее количество токенов")
    price_per_1k_tokens: Optional[str] = Field(None, description="Цена за 1K токенов")
    currency: str = Field(default="USD", description="Валюта (USD, RUB)")


class UsageStatistics(UsageStatisticsBase):
    """Полная модель статистики использования"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsageStatisticsCreate(UsageStatisticsBase):
    """Модель для создания записи статистики"""
    pass


class UsageStatisticsUpdate(BaseModel):
    """Модель для обновления статистики"""
    total_tokens: Optional[int] = None
    price_per_1k_tokens: Optional[str] = None
    currency: Optional[str] = None


class MonthlyUsageSummary(BaseModel):
    """Сводка использования за месяц"""
    year: int
    month: int
    total_tokens: int
    total_cost_usd: Optional[Decimal] = None
    total_cost_rub: Optional[Decimal] = None
    providers: dict[str, int]  # provider -> tokens
    models: dict[str, int]     # model -> tokens


class UsageLimits(BaseModel):
    """Лимиты использования"""
    monthly_token_limit: int = Field(default=1000000, description="Лимит токенов в месяц")
    monthly_cost_limit_usd: Decimal = Field(default=Decimal("100"), description="Лимит расходов в USD")
    cost_alert_threshold: float = Field(default=0.8, ge=0.1, le=1.0, description="Порог алерта (0.1-1.0)")
    auto_disable_on_limit: bool = Field(default=False, description="Автоотключение при превышении")
