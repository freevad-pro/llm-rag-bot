# PowerShell версия скрипта проверки подключения к PostgreSQL
# Использование: ./scripts/check_postgres_connection.ps1

Write-Host "🔍 Проверка подключения к PostgreSQL" -ForegroundColor Blue
Write-Host ""

# Определяем путь к docker-compose файлу
$ComposeFile = ""
$EnvType = ""

if ((Test-Path "/opt/llm-bot/app/docker-compose.prod.yml") -and (Test-Path "/opt/llm-bot/config/.env")) {
    $ComposeFile = "/opt/llm-bot/app/docker-compose.prod.yml"
    $EnvType = "Production"
} elseif ((Test-Path "docker-compose.prod.yml") -and (Test-Path "/opt/llm-bot/config/.env")) {
    $ComposeFile = "docker-compose.prod.yml"
    $EnvType = "Production"
} elseif (Test-Path "docker-compose.yml") {
    $ComposeFile = "docker-compose.yml"
    $EnvType = "Development"
} else {
    Write-Host "❌ Docker Compose файл не найден" -ForegroundColor Red
    Write-Host "Доступные варианты:"
    Write-Host "- Development: docker-compose.yml"
    Write-Host "- Production: docker-compose.prod.yml + /opt/llm-bot/config/.env"
    exit 1
}

Write-Host "📁 Используется: $EnvType ($ComposeFile)" -ForegroundColor Blue
Write-Host ""

# Проверяем готовность PostgreSQL
Write-Host "🔗 Проверяем подключение к PostgreSQL..." -ForegroundColor Blue

try {
    $result = docker-compose -f $ComposeFile exec postgres pg_isready -U postgres -q 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL запущен и готов к подключениям" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL не готов к подключениям" -ForegroundColor Red
        Write-Host "Для запуска выполните:"
        Write-Host "docker-compose -f $ComposeFile up -d postgres"
        exit 1
    }
} catch {
    Write-Host "❌ Ошибка подключения к PostgreSQL" -ForegroundColor Red
    Write-Host "Убедитесь что Docker запущен и выполните:"
    Write-Host "docker-compose -f $ComposeFile up -d postgres"
    exit 1
}

# Проверяем подключение к базе данных
Write-Host "🗄️  Проверяем подключение к базе catalog_db..." -ForegroundColor Blue

try {
    $version = docker-compose -f $ComposeFile exec postgres psql -U postgres -d catalog_db -t -c "SELECT version();" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Подключение к базе данных работает" -ForegroundColor Green
        $versionClean = $version.Trim()
        if ($versionClean) {
            Write-Host "📋 Версия: $versionClean" -ForegroundColor Blue
        }
    } else {
        Write-Host "❌ Ошибка подключения к базе данных" -ForegroundColor Red
        Write-Host ""
        Write-Host "🔧 Возможные причины:" -ForegroundColor Yellow
        Write-Host "1. Неверный пароль в конфигурации"
        Write-Host "2. База данных еще не создана"
        Write-Host "3. Проблемы с правами доступа"
        Write-Host ""
        Write-Host "📝 Проверьте настройки в:" -ForegroundColor Blue
        if ($EnvType -eq "Production") {
            Write-Host "- /opt/llm-bot/config/.env"
        } else {
            Write-Host "- .env файл (если используется)"
            Write-Host "- docker-compose.yml"
        }
        exit 1
    }
} catch {
    Write-Host "❌ Критическая ошибка при подключении к базе" -ForegroundColor Red
    exit 1
}

# Проверяем подключение приложения (если запущено)
Write-Host "🤖 Проверяем подключение приложения..." -ForegroundColor Blue

$appRunning = docker-compose -f $ComposeFile ps app 2>$null | Select-String "Up"
if ($appRunning) {
    Write-Host "✅ Контейнер приложения запущен" -ForegroundColor Green
    
    # Проверяем health endpoint
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Health check приложения прошел" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Health check приложения не прошел" -ForegroundColor Yellow
            Write-Host "Проверьте логи: docker-compose -f $ComposeFile logs app"
        }
    } catch {
        Write-Host "⚠️  Health check приложения не прошел" -ForegroundColor Yellow
        Write-Host "Проверьте логи: docker-compose -f $ComposeFile logs app"
    }
} else {
    Write-Host "⚠️  Контейнер приложения не запущен" -ForegroundColor Yellow
}

# Показываем статистику базы данных
Write-Host ""
Write-Host "📊 Статистика базы данных:" -ForegroundColor Blue

try {
    $tablesCount = docker-compose -f $ComposeFile exec postgres psql -U postgres -d catalog_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>$null
    $dbSize = docker-compose -f $ComposeFile exec postgres psql -U postgres -d catalog_db -t -c "SELECT pg_size_pretty(pg_database_size('catalog_db'));" 2>$null
    
    if ($tablesCount) {
        $tablesCountClean = $tablesCount.Trim()
        Write-Host "- Количество таблиц: $tablesCountClean"
    }
    if ($dbSize) {
        $dbSizeClean = $dbSize.Trim()
        Write-Host "- Размер базы данных: $dbSizeClean"
    }
} catch {
    Write-Host "- Не удалось получить статистику"
}

Write-Host ""
Write-Host "🎉 Проверка завершена успешно!" -ForegroundColor Green

# Полезные команды
Write-Host ""
Write-Host "💡 Полезные команды:" -ForegroundColor Blue
Write-Host "Подключиться к PostgreSQL:"
Write-Host "  docker-compose -f $ComposeFile exec postgres psql -U postgres -d catalog_db"
Write-Host ""
Write-Host "Посмотреть логи PostgreSQL:"
Write-Host "  docker-compose -f $ComposeFile logs postgres"
Write-Host ""
Write-Host "Посмотреть логи приложения:"
Write-Host "  docker-compose -f $ComposeFile logs app"
