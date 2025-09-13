"""
Domain services - business logic без внешних зависимостей.
Содержит классификацию запросов, управление диалогами и оркестратор поиска.
"""
from .query_classifier import QueryType, classify_user_query, is_contact_request, is_product_search, is_company_info_request
from .conversation_service import ConversationService, conversation_service
from .search_orchestrator import SearchOrchestrator, search_orchestrator

__all__ = [
    # Классификация запросов
    "QueryType",
    "classify_user_query",
    "is_contact_request", 
    "is_product_search",
    "is_company_info_request",
    
    # Управление диалогами
    "ConversationService",
    "conversation_service",
    
    # Оркестратор поиска
    "SearchOrchestrator", 
    "search_orchestrator",
]
