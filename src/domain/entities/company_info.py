"""
Сущность информации о компании
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CompanyInfo:
    """
    Информация о компании
    """
    id: Optional[int] = None
    filename: str = ""
    original_filename: str = ""
    file_size: int = 0
    file_type: str = ""  # DOCX, PDF, TXT
    content: str = ""  # Извлеченный текст
    version: int = 1
    is_active: bool = False
    uploaded_by: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class CompanyInfoUpload:
    """
    Данные для загрузки файла о компании
    """
    original_filename: str
    file_content: bytes
    file_size: int
    uploaded_by: int
