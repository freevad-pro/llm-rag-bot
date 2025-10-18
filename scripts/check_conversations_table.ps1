# PowerShell скрипт для проверки структуры таблицы conversations
# Использование: ./scripts/check_conversations_table.ps1

Write-Host "🔍 Проверка структуры таблицы conversations" -ForegroundColor Blue
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
    exit 1
}

Write-Host "📁 Используется: $EnvType ($ComposeFile)" -ForegroundColor Blue
Write-Host ""

# Проверяем существует ли таблица conversations
Write-Host "🔍 Проверяем существование таблицы conversations..." -ForegroundColor Blue

try {
    $tableExists = docker-compose -f $ComposeFile exec postgres psql -U postgres -d catalog_db -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'conversations');" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        $tableExistsClean = $tableExists.Trim()
        if ($tableExistsClean -eq "t") {
            Write-Host "✅ Таблица conversations существует" -ForegroundColor Green
        } else {
            Write-Host "❌ Таблица conversations не существует" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "❌ Ошибка при проверке таблицы" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Критическая ошибка при проверке таблицы" -ForegroundColor Red
    exit 1
}

# Получаем структуру таблицы
Write-Host "📋 Получаем структуру таблицы conversations..." -ForegroundColor Blue

try {
    $columns = docker-compose -f $ComposeFile exec postgres psql -U postgres -d catalog_db -t -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'conversations' ORDER BY ordinal_position;" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "📋 Структура таблицы conversations:" -ForegroundColor Blue
        
        $columnLines = $columns -split "`n" | Where-Object { $_.Trim() -ne "" }
        $hasStartedAt = $false
        $hasCreatedAt = $false
        
        foreach ($line in $columnLines) {
            $line = $line.Trim()
            if ($line) {
                $parts = $line -split "\|"
                if ($parts.Length -ge 3) {
                    $columnName = $parts[0].Trim()
                    $dataType = $parts[1].Trim()
                    $isNullable = $parts[2].Trim()
                    
                    Write-Host "  - $columnName ($dataType) $isNullable"
                    
                    if ($columnName -eq "started_at") {
                        $hasStartedAt = $true
                    }
                    if ($columnName -eq "created_at") {
                        $hasCreatedAt = $true
                    }
                }
            }
        }
        
        Write-Host ""
        
        # Анализируем проблему
        if ($hasStartedAt -and -not $hasCreatedAt) {
            Write-Host "⚠️  ПРОБЛЕМА НАЙДЕНА!" -ForegroundColor Red
            Write-Host "В таблице есть поле 'started_at', но должно быть 'created_at'" -ForegroundColor Red
            Write-Host "Нужно применить миграцию 008_rename_started_at_to_created_at" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "🔧 Решение:" -ForegroundColor Blue
            Write-Host "docker-compose -f $ComposeFile exec web python -m alembic upgrade head"
        } elseif ($hasCreatedAt -and -not $hasStartedAt) {
            Write-Host "✅ Структура корректна - поле 'created_at' присутствует" -ForegroundColor Green
        } elseif ($hasStartedAt -and $hasCreatedAt) {
            Write-Host "⚠️  В таблице есть и 'started_at' и 'created_at' - нужна проверка" -ForegroundColor Yellow
        } else {
            Write-Host "❌ Ни 'started_at', ни 'created_at' не найдены!" -ForegroundColor Red
        }
        
    } else {
        Write-Host "❌ Ошибка при получении структуры таблицы" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Критическая ошибка при получении структуры таблицы" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Проверка завершена!" -ForegroundColor Green
