"""
Сервис классификации запросов пользователей.
Определяет тип запроса согласно @vision.md и @product_idea.md.
Поддерживает гибкую настройку через базу данных.
"""
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.llm import llm_service
from src.infrastructure.services.classification_settings_service import classification_settings_service
from src.infrastructure.database.connection import get_session


class QueryType(Enum):
    """
    Типы запросов пользователей согласно @product_idea.md v1.1.
    """
    PRODUCT = "PRODUCT"           # Поиск конкретного товара
    SERVICE = "SERVICE"           # Вопрос об услугах компании  
    COMPANY_INFO = "COMPANY_INFO" # Вопросы о компании
    GENERAL = "GENERAL"           # Общий вопрос
    CONTACT = "CONTACT"           # Желание связаться с менеджером


async def classify_user_query(
    user_query: str, 
    session: AsyncSession
) -> QueryType:
    """
    Классифицирует запрос пользователя через LLM с поддержкой настроек из БД.
    
    Args:
        user_query: Запрос пользователя
        session: Сессия базы данных
        
    Returns:
        Тип запроса
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Получаем настройки классификации из БД
        settings = await classification_settings_service.get_active_settings(session)
        
        # ПРИОРИТЕТ 1: Быстрая классификация (если включена)
        if settings.get("enable_fast_classification", True):
            if await is_product_search_with_settings(user_query, settings):
                logger.debug(f"Запрос '{user_query[:50]}...' быстро классифицирован как PRODUCT (найден товар)")
                return QueryType.PRODUCT
                
            if await is_contact_request_with_settings(user_query, settings):
                logger.debug(f"Запрос '{user_query[:50]}...' быстро классифицирован как CONTACT")
                return QueryType.CONTACT
                
            if await is_company_info_request_with_settings(user_query, settings):
                logger.debug(f"Запрос '{user_query[:50]}...' быстро классифицирован как COMPANY_INFO")
                return QueryType.COMPANY_INFO
        
        # ПРИОРИТЕТ 2: LLM классификация (если включена)
        if settings.get("enable_llm_classification", True):
            classification_result = await llm_service.classify_user_query(
                user_query, 
                session
            )
            
            # Преобразуем результат в enum
            try:
                query_type = QueryType(classification_result)
                logger.debug(f"Запрос '{user_query[:50]}...' LLM классифицирован как {query_type.value}")
                return query_type
                
            except ValueError:
                logger.warning(f"Неизвестный тип классификации: {classification_result}")
                return QueryType.GENERAL
        
        # Fallback если все отключено
        logger.warning("Все методы классификации отключены, используем GENERAL")
        return QueryType.GENERAL
            
    except Exception as e:
        logger.error(f"Ошибка классификации запроса: {e}")
        return QueryType.GENERAL  # Безопасный fallback


# Оставляем старые функции для обратной совместимости
async def is_contact_request(user_query: str) -> bool:
    """
    Быстро определяет, является ли запрос желанием связаться с менеджером.
    Использует простые ключевые слова для быстрой проверки.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        True если это запрос на контакт
    """
    # Получаем настройки из БД
    async with get_session() as session:
        settings = await classification_settings_service.get_active_settings(session)
        contact_keywords = settings.get("contact_keywords", [])
    
    query_lower = user_query.lower()
    return any(keyword in query_lower for keyword in contact_keywords)


async def is_product_search(user_query: str) -> bool:
    """
    Быстро определяет, является ли запрос поиском товара.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        True если это поиск товара
    """
    # Получаем настройки из БД
    async with get_session() as session:
        settings = await classification_settings_service.get_active_settings(session)
        specific_products = settings.get("specific_products", [])
        general_product_words = settings.get("product_keywords", [])
        availability_phrases = settings.get("availability_phrases", [])
        search_words = settings.get("search_words", [])
    
    query_lower = user_query.lower()
    
    # Проверяем конкретные товары (приоритет 1)
    for product in specific_products:
        if product in query_lower:
            return True
    
    # Проверяем фразы о наличии + общие слова товаров (приоритет 2)
    has_availability_phrase = any(phrase in query_lower for phrase in availability_phrases)
    has_general_product_word = any(word in query_lower for word in general_product_words)
    
    if has_availability_phrase and has_general_product_word:
        return True
    
    # Проверяем фразы о наличии + конкретные товары (приоритет 2.5)
    if has_availability_phrase:
        for product in specific_products:
            if product in query_lower:
                return True
    
    # Проверяем слова поиска (приоритет 3)
    if any(word in query_lower for word in search_words):
        return True
    
    return False


async def is_company_info_request(user_query: str) -> bool:
    """
    Быстро определяет, является ли запрос вопросом о компании.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        True если это вопрос о компании
    """
    # Получаем настройки из БД
    async with get_session() as session:
        settings = await classification_settings_service.get_active_settings(session)
        company_keywords = settings.get("company_keywords", [])
    
    query_lower = user_query.lower()
    return any(keyword in query_lower for keyword in company_keywords)


def get_classification_confidence(user_query: str) -> dict:
    """
    Возвращает вероятности для каждого типа запроса на основе ключевых слов.
    Используется для отладки и анализа.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        Словарь с вероятностями для каждого типа
    """
    confidence = {
        "PRODUCT": 0.0,
        "SERVICE": 0.0, 
        "COMPANY_INFO": 0.0,
        "GENERAL": 0.0,
        "CONTACT": 0.0
    }
    
    query_lower = user_query.lower()
    
    # Подсчитываем ключевые слова для каждой категории
    product_keywords = ["товар", "product", "оборудование", "запчасть", "найти", "артикул"]
    service_keywords = ["услуга", "service", "доставка", "гарантия", "поддержка", "сервис"]
    company_keywords = ["компания", "о вас", "адрес", "контакты", "история"]
    contact_keywords = ["менеджер", "связаться", "позвонить", "заказать", "цена"]
    general_keywords = ["привет", "hello", "спасибо", "thanks", "помощь", "help"]
    
    for keyword in product_keywords:
        if keyword in query_lower:
            confidence["PRODUCT"] += 0.2
    
    for keyword in service_keywords:
        if keyword in query_lower:
            confidence["SERVICE"] += 0.2
    
    for keyword in company_keywords:
        if keyword in query_lower:
            confidence["COMPANY_INFO"] += 0.2
    
    for keyword in contact_keywords:
        if keyword in query_lower:
            confidence["CONTACT"] += 0.2
    
    for keyword in general_keywords:
        if keyword in query_lower:
            confidence["GENERAL"] += 0.2
    
    # Нормализуем вероятности
    total = sum(confidence.values())
    if total > 0:
        for key in confidence:
            confidence[key] = min(confidence[key] / total, 1.0)
    else:
        confidence["GENERAL"] = 1.0
    
    return confidence


# Новые функции с поддержкой настроек из БД
async def is_product_search_with_settings(user_query: str, settings: Dict[str, Any]) -> bool:
    """
    Определяет, является ли запрос поиском товара, используя настройки из БД.
    
    Args:
        user_query: Запрос пользователя
        settings: Настройки классификации из БД
        
    Returns:
        True если это поиск товара
    """
    query_lower = user_query.lower()
    
    # Получаем ключевые слова из настроек
    specific_products = settings.get("specific_products", [])
    general_product_words = settings.get("product_keywords", [])
    availability_phrases = settings.get("availability_phrases", [])
    search_words = settings.get("search_words", [])
    
    # Проверяем конкретные товары (приоритет 1)
    for product in specific_products:
        if product.lower() in query_lower:
            return True
    
    # Проверяем фразы о наличии + общие слова товаров (приоритет 2)
    has_availability_phrase = any(phrase.lower() in query_lower for phrase in availability_phrases)
    has_general_product_word = any(word.lower() in query_lower for word in general_product_words)
    
    if has_availability_phrase and has_general_product_word:
        return True
    
    # Проверяем фразы о наличии + конкретные товары (приоритет 2.5)
    if has_availability_phrase:
        for product in specific_products:
            if product.lower() in query_lower:
                return True
    
    # Проверяем слова поиска (приоритет 3)
    if any(word.lower() in query_lower for word in search_words):
        return True
    
    return False


async def is_contact_request_with_settings(user_query: str, settings: Dict[str, Any]) -> bool:
    """
    Определяет, является ли запрос желанием связаться с менеджером, используя настройки из БД.
    
    Args:
        user_query: Запрос пользователя
        settings: Настройки классификации из БД
        
    Returns:
        True если это запрос на контакт
    """
    contact_keywords = settings.get("contact_keywords", [])
    query_lower = user_query.lower()
    return any(keyword.lower() in query_lower for keyword in contact_keywords)


async def is_company_info_request_with_settings(user_query: str, settings: Dict[str, Any]) -> bool:
    """
    Определяет, является ли запрос вопросом о компании, используя настройки из БД.
    
    Args:
        user_query: Запрос пользователя
        settings: Настройки классификации из БД
        
    Returns:
        True если это вопрос о компании
    """
    company_keywords = settings.get("company_keywords", [])
    query_lower = user_query.lower()
    return any(keyword.lower() in query_lower for keyword in company_keywords)
