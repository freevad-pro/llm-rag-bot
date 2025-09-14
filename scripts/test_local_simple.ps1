# Простой PowerShell скрипт для локального тестирования
param(
    [string]$Command = "help"
)

function Write-Info {
    param([string]$Message)
    Write-Host "INFO: $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "SUCCESS: $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

# Переходим в директорию проекта
Set-Location (Split-Path -Parent (Split-Path -Path $PSScriptRoot))

function Show-Help {
    Write-Host "🧪 Локальное тестирование ИИ-бота" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Доступные команды:"
    Write-Host "  setup    - Настроить тестовую среду"
    Write-Host "  start    - Запустить тестовую среду"
    Write-Host "  stop     - Остановить тестовую среду"
    Write-Host "  test     - Запустить тесты"
    Write-Host "  status   - Показать статус"
    Write-Host "  clean    - Очистить среду"
    Write-Host "  help     - Показать эту справку"
}

function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker не установлен!"
    }
}

switch ($Command.ToLower()) {
    "setup" {
        Write-Info "🔧 Настройка тестовой среды..."
        Test-Docker
        
        # Создаем директории
        New-Item -ItemType Directory -Path "data\test_chroma", "data\test_uploads", "test-results", "htmlcov" -Force | Out-Null
        
        # Создаем .env.test файл
        if (-not (Test-Path ".env.test")) {
            @"
DEBUG=true
ENVIRONMENT=test
DATABASE_URL=postgresql+asyncpg://test_user:test_pass@localhost:5433/test_catalog_db
BOT_TOKEN=test_bot_token_for_local_testing
DEFAULT_LLM_PROVIDER=test
"@ | Out-File -FilePath ".env.test" -Encoding UTF8
            Write-Success "Создан .env.test файл"
        }
        
        # Собираем образы
        Write-Info "🐳 Собираем тестовые образы..."
        docker compose -f docker-compose.test.yml build
        Write-Success "Тестовая среда настроена!"
    }
    
    "start" {
        Write-Info "🚀 Запуск тестовой среды..."
        Test-Docker
        
        docker compose -f docker-compose.test.yml up -d postgres-test
        Start-Sleep -Seconds 5
        
        docker compose -f docker-compose.test.yml up -d app-test
        Start-Sleep -Seconds 10
        
        Write-Success "Тестовая среда запущена!"
        Write-Info "🌐 Приложение: http://localhost:8001"
        Write-Info "🗄️ БД: localhost:5433"
    }
    
    "stop" {
        Write-Info "🛑 Остановка тестовой среды..."
        docker compose -f docker-compose.test.yml down
        Write-Success "Тестовая среда остановлена"
    }
    
    "test" {
        Write-Info "🧪 Запуск тестов..."
        docker compose -f docker-compose.test.yml run --rm pytest-runner test
    }
    
    "status" {
        Write-Info "📊 Статус сервисов..."
        docker compose -f docker-compose.test.yml ps
    }
    
    "clean" {
        Write-Info "🧹 Очистка тестовой среды..."
        docker compose -f docker-compose.test.yml down -v --remove-orphans
        Write-Success "Тестовая среда очищена"
    }
    
    "help" {
        Show-Help
    }
    
    default {
        Write-Warning "Неизвестная команда: $Command"
        Show-Help
    }
}

Write-Host ""
Write-Info "Скрипт завершен"