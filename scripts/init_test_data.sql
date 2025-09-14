-- Инициализация тестовых данных
-- Этот скрипт выполняется при создании тестовой БД

-- Создаем тестового пользователя для интеграционных тестов
INSERT INTO users (chat_id, telegram_user_id, username, first_name, last_name, phone, email) 
VALUES (999999, 888888, 'test_user', 'Тестовый', 'Пользователь', '+79001234567', 'test@example.com')
ON CONFLICT (chat_id) DO NOTHING;

-- Создаем тестовые настройки LLM
INSERT INTO llm_settings (provider, config, is_active, created_at)
VALUES 
    ('test', '{"api_key": "test_key", "model": "test-model"}', true, NOW()),
    ('openai', '{"api_key": "test_openai_key", "model": "gpt-3.5-turbo"}', false, NOW())
ON CONFLICT DO NOTHING;
