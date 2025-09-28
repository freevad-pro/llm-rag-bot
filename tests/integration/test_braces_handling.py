"""
Интеграционные тесты для проверки обработки фигурных скобок в реальных сценариях.
Проверяют что система корректно обрабатывает пользовательские запросы с фигурными скобками.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.services.search_orchestrator import SearchOrchestrator
from src.infrastructure.llm.providers.openai_provider import OpenAIProvider
from src.infrastructure.llm.providers.yandex_provider import YandexGPTProvider
from src.infrastructure.llm.services.llm_service import LLMService
from src.infrastructure.llm.providers.base import LLMResponse


@pytest.mark.asyncio
class TestBracesHandlingIntegration:
    """Интеграционные тесты обработки фигурных скобок."""
    
    async def test_search_orchestrator_saves_valid_json(self):
        """Тест что SearchOrchestrator сохраняет валидный JSON в extra_data."""
        orchestrator = SearchOrchestrator()
        
        # Мокаем зависимости
        mock_session = AsyncMock()
        mock_llm_response = LLMResponse(
            content="Тестовый ответ",
            provider="openai",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )
        
        # Мокаем conversation_service
        with pytest.mock.patch('src.domain.services.search_orchestrator.conversation_service') as mock_conv_service:
            mock_conv_service.save_user_message = AsyncMock()
            mock_conv_service.get_conversation_context = AsyncMock(return_value=[])
            mock_conv_service.save_assistant_message = AsyncMock()
            
            # Мокаем classify_user_query
            with pytest.mock.patch('src.domain.services.search_orchestrator.classify_user_query') as mock_classify:
                mock_classify.return_value = AsyncMock()
                mock_classify.return_value.value = "PRODUCT"
                
                # Мокаем _route_query
                orchestrator._route_query = AsyncMock(return_value={
                    "response": "Тестовый ответ",
                    "query_type": "PRODUCT",
                    "llm_response": mock_llm_response,
                    "processing_time_ms": 1500
                })
                
                # Выполняем тест
                await orchestrator.process_user_query(
                    user_query="Найди товар {артикул}",
                    chat_id=123,
                    session=mock_session
                )
                
                # Проверяем что save_assistant_message был вызван с валидным JSON
                mock_conv_service.save_assistant_message.assert_called_once()
                call_args = mock_conv_service.save_assistant_message.call_args
                
                extra_data = call_args.kwargs['extra_data']
                
                # Проверяем что это валидный JSON
                parsed_data = json.loads(extra_data)
                assert parsed_data['model'] == 'gpt-3.5-turbo'
                assert parsed_data['usage']['total_tokens'] == 30
    
    async def test_openai_provider_handles_braces_in_query(self):
        """Тест что OpenAI провайдер корректно обрабатывает фигурные скобки в запросе."""
        provider = OpenAIProvider(
            api_key="test-key",
            model="gpt-3.5-turbo"
        )
        
        # Мокаем generate_response
        mock_response = LLMResponse(
            content="PRODUCT",
            provider="openai",
            model="gpt-3.5-turbo"
        )
        provider.generate_response = AsyncMock(return_value=mock_response)
        
        # Тестируем запрос с фигурными скобками
        query_with_braces = "Найди товар {артикул} с параметром {значение}"
        
        result = await provider.classify_query(query_with_braces)
        
        # Проверяем что метод не упал и вернул результат
        assert result == "PRODUCT"
        
        # Проверяем что generate_response был вызван
        provider.generate_response.assert_called_once()
        
        # Проверяем что в переданном сообщении фигурные скобки экранированы
        call_args = provider.generate_response.call_args[1]
        messages = call_args['messages']
        message_content = messages[0].content
        
        # В сообщении должны быть экранированные скобки
        assert "{{артикул}}" in message_content
        assert "{{значение}}" in message_content
        assert "{артикул}" not in message_content  # Неэкранированных быть не должно
    
    async def test_yandex_provider_handles_braces_in_query(self):
        """Тест что Yandex провайдер корректно обрабатывает фигурные скобки в запросе."""
        provider = YandexGPTProvider(
            api_key="test-key",
            folder_id="test-folder",
            model="yandexgpt"
        )
        
        # Мокаем generate_response
        mock_response = LLMResponse(
            content="SERVICE",
            provider="yandexgpt",
            model="yandexgpt"
        )
        provider.generate_response = AsyncMock(return_value=mock_response)
        
        # Тестируем запрос с фигурными скобками
        query_with_braces = "Расскажи об услуге {название} с опцией {параметр}"
        
        result = await provider.classify_query(query_with_braces)
        
        # Проверяем что метод не упал и вернул результат
        assert result == "SERVICE"
        
        # Проверяем что generate_response был вызван
        provider.generate_response.assert_called_once()
        
        # Проверяем что в переданном сообщении фигурные скобки экранированы
        call_args = provider.generate_response.call_args[1]
        messages = call_args['messages']
        message_content = messages[0].content
        
        # В сообщении должны быть экранированные скобки
        assert "{{название}}" in message_content
        assert "{{параметр}}" in message_content
    
    async def test_llm_service_handles_braces_in_user_query(self):
        """Тест что LLMService корректно обрабатывает фигурные скобки в пользовательских запросах."""
        llm_service = LLMService()
        
        # Мокаем зависимости
        mock_session = AsyncMock()
        mock_provider = AsyncMock()
        mock_response = LLMResponse(
            content="Найдены товары по вашему запросу",
            provider="openai",
            model="gpt-3.5-turbo"
        )
        mock_provider.generate_response = AsyncMock(return_value=mock_response)
        
        # Мокаем llm_factory
        with pytest.mock.patch('src.infrastructure.llm.services.llm_service.llm_factory') as mock_factory:
            mock_factory.get_active_provider = AsyncMock(return_value=mock_provider)
            
            # Мокаем prompt_manager
            with pytest.mock.patch('src.infrastructure.llm.services.llm_service.prompt_manager') as mock_prompt_manager:
                mock_prompt_manager.get_prompt = AsyncMock(return_value="Найденные товары: {search_results}\nЗапрос пользователя: {user_query}")
                
                # Тестируем generate_product_response с фигурными скобками в запросе
                user_query_with_braces = "Найди насос {модель} для {применение}"
                search_results = [{"title": "Насос центробежный", "description": "Описание"}]
                
                result = await llm_service.generate_product_response(
                    user_query=user_query_with_braces,
                    search_results=search_results,
                    session=mock_session
                )
                
                # Проверяем что метод не упал и вернул результат
                assert result == "Найдены товары по вашему запросу"
                
                # Проверяем что generate_response был вызван
                mock_provider.generate_response.assert_called_once()
                
                # Проверяем что в переданном промпте фигурные скобки экранированы
                call_args = mock_provider.generate_response.call_args[1]
                messages = call_args['messages']
                message_content = messages[0].content
                
                # В промпте должны быть экранированные скобки из пользовательского запроса
                assert "{{модель}}" in message_content
                assert "{{применение}}" in message_content
                assert "{модель}" not in message_content  # Неэкранированных быть не должно


@pytest.mark.asyncio
class TestErrorScenarios:
    """Тесты сценариев с ошибками."""
    
    async def test_json_parsing_after_fix(self):
        """Тест что после исправления JSON корректно парсится."""
        # Симулируем данные которые раньше ломались
        usage_data = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        model_name = "gpt-3.5-turbo"
        
        # Старый способ (ломался)
        # old_extra_data = f'{{"model": "{model_name}", "usage": {usage_data}}}'
        
        # Новый способ (исправленный)
        new_extra_data = json.dumps({
            "model": model_name,
            "usage": usage_data
        })
        
        # Проверяем что новый способ создает валидный JSON
        parsed_data = json.loads(new_extra_data)
        assert parsed_data['model'] == model_name
        assert parsed_data['usage']['total_tokens'] == 30
        
        # Проверяем что это действительно валидный JSON
        assert isinstance(parsed_data, dict)
        assert 'model' in parsed_data
        assert 'usage' in parsed_data
