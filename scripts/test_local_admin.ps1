# Скрипт для локального тестирования админ-панели
# Запуск: PowerShell .\scripts\test_local_admin.ps1

Write-Host "🚀 ЛОКАЛЬНОЕ ТЕСТИРОВАНИЕ АДМИН-ПАНЕЛИ" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Проверяем наличие Docker
Write-Host "`n🐳 Проверка Docker..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerVersion = docker --version
    Write-Host "✓ Docker найден: $dockerVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Docker не найден! Установите Docker Desktop" -ForegroundColor Red
    exit 1
}

# Проверяем наличие docker-compose
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeVersion = docker-compose --version
    Write-Host "✓ Docker Compose найден: $composeVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Docker Compose не найден!" -ForegroundColor Red
    exit 1
}

# Копируем тестовые настройки
Write-Host "`n📝 Подготовка настроек..." -ForegroundColor Yellow
Copy-Item "env.test" ".env" -Force
Write-Host "✓ Скопированы настройки из env.test в .env" -ForegroundColor Green

# Останавливаем существующие контейнеры
Write-Host "`n🛑 Остановка существующих контейнеров..." -ForegroundColor Yellow
docker-compose down 2>$null
Write-Host "✓ Контейнеры остановлены" -ForegroundColor Green

# Создаем директории для данных
Write-Host "`n📁 Создание директорий для данных..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data\persistent\chroma" | Out-Null
New-Item -ItemType Directory -Force -Path "data\uploads" | Out-Null
Write-Host "✓ Директории созданы" -ForegroundColor Green

# Собираем образы
Write-Host "`n🔨 Сборка Docker образов..." -ForegroundColor Yellow
docker-compose build --no-cache app
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка сборки образа" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Образ собран успешно" -ForegroundColor Green

# Запускаем сервисы
Write-Host "`n🚀 Запуск сервисов..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка запуска сервисов" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Сервисы запущены" -ForegroundColor Green

# Ждем запуска базы данных
Write-Host "`n⏳ Ожидание запуска PostgreSQL..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверяем статус контейнеров
Write-Host "`n📋 Статус контейнеров:" -ForegroundColor Yellow
docker-compose ps

# Запускаем тестирование
Write-Host "`n🧪 Запуск тестирования..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
python scripts/test_admin_panel.py

# Показываем логи если есть ошибки
Write-Host "`n📊 Последние логи приложения:" -ForegroundColor Yellow
docker-compose logs --tail=20 app

Write-Host "`n✅ ГОТОВО К ТЕСТИРОВАНИЮ!" -ForegroundColor Green
Write-Host "🌐 Откройте браузер: http://localhost:8000/admin/" -ForegroundColor Cyan
Write-Host "📊 Health check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "📜 API docs: http://localhost:8000/docs" -ForegroundColor Cyan

Write-Host "`n⚙️  Полезные команды:" -ForegroundColor Yellow
Write-Host "  Логи:        docker-compose logs -f app" -ForegroundColor White
Write-Host "  Остановка:   docker-compose down" -ForegroundColor White
Write-Host "  Перезапуск:  docker-compose restart app" -ForegroundColor White
Write-Host "  Статус:      docker-compose ps" -ForegroundColor White

Write-Host "`n🎯 Для полного тестирования авторизации:" -ForegroundColor Yellow
Write-Host "1. Замените в .env на ваши реальные Telegram ID" -ForegroundColor White
Write-Host "2. Добавьте реальный BOT_TOKEN от @BotFather" -ForegroundColor White
Write-Host "3. Перезапустите: docker-compose restart app" -ForegroundColor White
