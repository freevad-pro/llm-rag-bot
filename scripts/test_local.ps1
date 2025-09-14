# PowerShell скрипт для локального тестирования на Windows
# Использование: .\scripts\test_local.ps1 [команда]

param(
    [string]$Command = "help",
    [string[]]$Args = @()
)

# Функции для цветного вывода
function Write-Log { 
    param([string]$Message)
    Write-Host "[LOCAL TEST] $Message" -ForegroundColor Blue 
}

function Write-Success { 
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green 
}

function Write-Warning { 
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow 
}

function Write-Error { 
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red 
    exit 1
}

function Write-Info { 
    param([string]$Message)
    Write-Host "ℹ️ $Message" -ForegroundColor Cyan 
}

# Переходим в директорию проекта
Set-Location (Split-Path -Parent (Split-Path -Path $PSScriptRoot))

# Функция показа справки
function Show-Help {
    Write-Host "🧪 Локальное тестирование ИИ-бота" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Использование: .\scripts\test_local.ps1 [команда] [опции]"
    Write-Host ""
    Write-Host "Управление средой:" -ForegroundColor Green
    Write-Host "  setup      - Настроить тестовую среду"
    Write-Host "  start      - Запустить тестовую среду"
    Write-Host "  stop       - Остановить тестовую среду"
    Write-Host "  clean      - Очистить тестовую среду"
    Write-Host "  logs       - Показать логи сервисов"
    Write-Host ""
    Write-Host "Тестирование:" -ForegroundColor Green
    Write-Host "  test       - Запустить все тесты"
    Write-Host "  test-unit  - Только unit тесты"
    Write-Host "  test-int   - Только интеграционные тесты"
    Write-Host "  test-e2e   - Только E2E тесты"
    Write-Host "  coverage   - Тесты с покрытием кода"
    Write-Host ""
    Write-Host "Качество кода:" -ForegroundColor Green
    Write-Host "  lint       - Проверка качества кода"
    Write-Host "  format     - Форматирование кода"
    Write-Host "  check      - Полная проверка (lint + test)"
    Write-Host ""
    Write-Host "Отладка:" -ForegroundColor Green
    Write-Host "  shell      - Интерактивная оболочка в контейнере"
    Write-Host "  db-shell   - Подключение к тестовой БД"
    Write-Host "  status     - Статус всех сервисов"
    Write-Host ""
}

# Функция проверки Docker
function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker не установлен!"
    }
    
    if (-not (docker compose version 2>$null)) {
        Write-Error "Docker Compose не установлен!"
    }
}

# Функция настройки тестовой среды
function Setup-Environment {
    Write-Log "🔧 Настройка тестовой среды..."
    
    # Создаем директории для тестов
    New-Item -ItemType Directory -Path "data\test_chroma", "data\test_uploads", "test-results", "htmlcov" -Force | Out-Null
    
    # Создаем тестовый .env файл если его нет
    if (-not (Test-Path ".env.test")) {
        Write-Log "📝 Создаем .env.test файл..."
        @"
# Тестовая конфигурация
DEBUG=true
ENVIRONMENT=test
DATABASE_URL=postgresql+asyncpg://test_user:test_pass@localhost:5433/test_catalog_db
BOT_TOKEN=test_bot_token_for_local_testing
DEFAULT_LLM_PROVIDER=test
MANAGER_TELEGRAM_CHAT_ID=
ADMIN_TELEGRAM_IDS=
LEAD_INACTIVITY_THRESHOLD=1
"@ | Out-File -FilePath ".env.test" -Encoding UTF8
        Write-Success "Создан .env.test файл"
    }
    
    # Создаем скрипт инициализации тестовых данных
    if (-not (Test-Path "scripts\init_test_data.sql")) {
        Write-Log "📝 Создаем скрипт инициализации тестовых данных..."
        @"
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
"@ | Out-File -FilePath "scripts\init_test_data.sql" -Encoding UTF8
        Write-Success "Создан скрипт инициализации тестовых данных"
    }
    
    Write-Success "Тестовая среда настроена"
}

# Основная логика
switch ($Command.ToLower()) {
    "setup" {
        Test-Docker
        Setup-Environment
        Write-Log "🐳 Собираем тестовые образы..."
        docker compose -f docker-compose.test.yml build
        Write-Success "Тестовая среда готова к использованию"
    }
    
    "start" {
        Test-Docker
        Write-Log "🚀 Запуск тестовой среды..."
        docker compose -f docker-compose.test.yml up -d postgres-test
        
        Write-Log "⏳ Ожидание готовности PostgreSQL..."
        Start-Sleep -Seconds 5
        
        docker compose -f docker-compose.test.yml up -d app-test
        
        Write-Log "⏳ Ожидание готовности приложения..."
        Start-Sleep -Seconds 10
        
        # Проверяем статус
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -UseBasicParsing
            Write-Success "Тестовая среда запущена!"
            Write-Info "🌐 Приложение: http://localhost:8001"
            Write-Info "🗄️ БД: localhost:5433"
            Write-Info "📋 Health: http://localhost:8001/health"
        }
        catch {
            Write-Warning "Приложение не отвечает. Проверьте логи: .\scripts\test_local.ps1 logs"
        }
    }
    
    "stop" {
        Write-Log "🛑 Остановка тестовой среды..."
        docker compose -f docker-compose.test.yml down
        Write-Success "Тестовая среда остановлена"
    }
    
    "clean" {
        Write-Log "🧹 Очистка тестовой среды..."
        docker compose -f docker-compose.test.yml down -v --remove-orphans
        docker compose -f docker-compose.test.yml build --no-cache
        Remove-Item -Path "data\test_chroma\*", "data\test_uploads\*", "test-results\*", "htmlcov\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success "Тестовая среда очищена"
    }
    
    "test" {
        Write-Log "🧪 Запуск всех тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test $Args
    }
    
    "test-unit" {
        Write-Log "⚡ Запуск unit тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m unit $Args
    }
    
    "test-int" {
        Write-Log "🔗 Запуск интеграционных тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m integration $Args
    }
    
    "test-e2e" {
        Write-Log "🎯 Запуск E2E тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m e2e $Args
    }
    
    "coverage" {
        Write-Log "📊 Запуск тестов с покрытием..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner coverage $Args
        Write-Success "Отчет сохранен в htmlcov\index.html"
    }
    
    "lint" {
        Write-Log "🔍 Проверка качества кода..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner lint
    }
    
    "format" {
        Write-Log "✨ Форматирование кода..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner format
    }
    
    "check" {
        Write-Log "🔎 Полная проверка кода..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner lint
        docker compose -f docker-compose.test.yml run --rm pytest-runner test -m "unit or (integration and not slow)"
        Write-Success "Полная проверка завершена"
    }
    
    "shell" {
        Write-Log "🐚 Интерактивная оболочка..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner shell
    }
    
    "db-shell" {
        Write-Log "🗄️ Подключение к тестовой БД..."
        docker compose -f docker-compose.test.yml exec postgres-test psql -U test_user -d test_catalog_db
    }
    
    "logs" {
        Write-Log "📋 Логи сервисов..."
        $service = if ($Args.Count -gt 0) { $Args[0] } else { "" }
        docker compose -f docker-compose.test.yml logs -f $service
    }
    
    "status" {
        Write-Log "📊 Статус сервисов..."
        docker compose -f docker-compose.test.yml ps
        Write-Host ""
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -UseBasicParsing
            Write-Success "Приложение работает: http://localhost:8001"
        }
        catch {
            Write-Warning "Приложение недоступно"
        }
    }
    
    { $_ -in "help", "-h", "--help" } {
        Show-Help
    }
    
    default {
        Write-Error "Неизвестная команда: $Command"
        Show-Help
    }
}
