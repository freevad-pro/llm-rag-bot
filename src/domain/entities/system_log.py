"""
Domain entity для системных логов
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """Уровни логирования"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @property
    def display_name(self) -> str:
        """Отображаемое название"""
        names = {
            self.DEBUG: "Отладка",
            self.INFO: "Информация", 
            self.WARNING: "Предупреждение",
            self.ERROR: "Ошибка",
            self.CRITICAL: "Критическая ошибка"
        }
        return names.get(self, self.value)

    @property
    def badge_color(self) -> str:
        """Цвет для Bootstrap badge"""
        colors = {
            self.DEBUG: "secondary",
            self.INFO: "info",
            self.WARNING: "warning", 
            self.ERROR: "danger",
            self.CRITICAL: "dark"
        }
        return colors.get(self, "secondary")

    @property
    def icon(self) -> str:
        """Иконка Bootstrap Icons"""
        icons = {
            self.DEBUG: "bi-bug",
            self.INFO: "bi-info-circle",
            self.WARNING: "bi-exclamation-triangle",
            self.ERROR: "bi-x-circle",
            self.CRITICAL: "bi-exclamation-octagon"
        }
        return icons.get(self, "bi-circle")


@dataclass
class SystemLog:
    """Сущность системного лога"""
    id: Optional[int]
    level: LogLevel
    message: str
    module: str
    function: str
    line_number: int
    timestamp: datetime
    extra_data: Optional[dict] = None

    @property
    def level_display(self) -> str:
        """Отображаемый уровень лога"""
        return self.level.display_name

    @property
    def level_badge_color(self) -> str:
        """Цвет badge для уровня"""
        return self.level.badge_color

    @property
    def level_icon(self) -> str:
        """Иконка для уровня"""
        return self.level.icon

    @property
    def short_message(self) -> str:
        """Сокращенное сообщение для списков"""
        if len(self.message) <= 100:
            return self.message
        return self.message[:97] + "..."

    @property
    def location(self) -> str:
        """Место в коде"""
        return f"{self.module}.{self.function}:{self.line_number}"

    @property
    def formatted_timestamp(self) -> str:
        """Отформатированное время"""
        return self.timestamp.strftime("%d.%m.%Y %H:%M:%S")

    @property
    def is_error(self) -> bool:
        """Является ли ошибкой"""
        return self.level in [LogLevel.ERROR, LogLevel.CRITICAL]

    @property
    def is_important(self) -> bool:
        """Важный лог"""
        return self.level in [LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]


