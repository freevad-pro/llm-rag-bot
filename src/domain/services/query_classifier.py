"""
Сервис классификации запросов пользователей.
Определяет тип запроса согласно @vision.md и @product_idea.md.
"""
import logging
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.llm import llm_service


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
    Классифицирует запрос пользователя через LLM.
    
    Args:
        user_query: Запрос пользователя
        session: Сессия базы данных
        
    Returns:
        Тип запроса
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Сначала проверяем быстрые ключевые слова
        if await is_contact_request(user_query):
            logger.debug(f"Запрос '{user_query[:50]}...' быстро классифицирован как CONTACT")
            return QueryType.CONTACT
            
        if await is_product_search(user_query):
            logger.debug(f"Запрос '{user_query[:50]}...' быстро классифицирован как PRODUCT")
            return QueryType.PRODUCT
            
        if await is_company_info_request(user_query):
            logger.debug(f"Запрос '{user_query[:50]}...' быстро классифицирован как COMPANY_INFO")
            return QueryType.COMPANY_INFO
        
        # Если быстрая проверка не сработала, используем LLM
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
            
    except Exception as e:
        logger.error(f"Ошибка классификации запроса: {e}")
        return QueryType.GENERAL  # Безопасный fallback


async def is_contact_request(user_query: str) -> bool:
    """
    Быстро определяет, является ли запрос желанием связаться с менеджером.
    Использует простые ключевые слова для быстрой проверки.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        True если это запрос на контакт
    """
    contact_keywords = [
        "менеджер", "manager", 
        "связаться", "connect", "contact",
        "позвонить", "call", "phone",
        "заказать", "order",
        "купить", "buy", "purchase",
        "цена", "price", "стоимость", "cost",
        "консультация", "consultation",
        "помощь менеджера", "manager help",
        "человек", "person", "оператор", "operator"
    ]
    
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
    product_keywords = [
        "товар", "product",
        "оборудование", "equipment", 
        "запчасть", "part", "spare",
        "деталь", "detail",
        "артикул", "article", "sku",
        "модель", "model",
        "найти", "find", "искать", "search",
        "нужен", "need", "требуется", "required",
        "болт", "винт", "гайка", "шайба",  # Специфичные товары
        "подшипник", "bearing",
        "фильтр", "filter",
        "масло", "oil",
        "ремень", "belt",
        "сверло", "drill", "bit",  # Добавляем сверла
        "керн", "core",  # Добавляем керн
        "есть ли у вас", "продаете ли", "найдется ли", "имеется ли",  # Вопросы о наличии
        "у вас есть", "в наличии", "есть в наличии"
    ]
    
    query_lower = user_query.lower()
    return any(keyword in query_lower for keyword in product_keywords)


async def is_company_info_request(user_query: str) -> bool:
    """
    Быстро определяет, является ли запрос вопросом о компании.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        True если это вопрос о компании
    """
    company_keywords = [
        "компания", "company",
        "о вас", "about you", "about us",
        "кто вы", "who are you",
        "где находится", "where located", "адрес", "address",
        "контакты", "contacts",
        "телефон компании", "company phone",
        "как называется", "what is the name",
        "история", "history",
        "когда основана", "when founded",
        "сколько лет", "how old",
        "чем занимаетесь", "what do you do",
        "ваши услуги", "your services"
    ]
    
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
