# Makefile для удобного запуска команд ИИ-бота
# Использование: make [команда]

.PHONY: help setup test clean lint format check dev prod

# Цвета для вывода
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# Функция вывода
define log
	@echo "$(BLUE)[MAKE]$(NC) $(1)"
endef

define success
	@echo "$(GREEN)✅$(NC) $(1)"
endef

# По умолчанию показываем справку
help: ## Показать справку
	@echo "$(BLUE)🤖 ИИ-бот - Команды разработки$(NC)"
	@echo ""
	@echo "$(GREEN)Локальная разработка:$(NC)"
	@echo "  setup      - Настроить все среды"
	@echo "  dev        - Запустить dev среду"
	@echo "  test-local - Запустить локальные тесты"
	@echo "  clean      - Очистить все"
	@echo ""
	@echo "$(GREEN)Тестирование:$(NC)"
	@echo "  test       - Все тесты"
	@echo "  test-unit  - Unit тесты"
	@echo "  test-int   - Интеграционные тесты"
	@echo "  test-e2e   - E2E тесты"
	@echo "  coverage   - Покрытие кода"
	@echo ""
	@echo "$(GREEN)Качество кода:$(NC)"
	@echo "  lint       - Проверка кода"
	@echo "  format     - Форматирование"
	@echo "  check      - Полная проверка"
	@echo ""
	@echo "$(GREEN)Production:$(NC)"
	@echo "  prod-test  - Тесты на production"
	@echo "  deploy     - Деплой с тестами"
	@echo ""

# Настройка всех сред
setup: ## Настроить dev и test среды
	$(call log,"🔧 Настройка сред разработки...")
	@./scripts/test_local.sh setup
	$(call success,"Среды настроены")

# Локальная разработка
dev: ## Запустить dev среду
	$(call log,"🚀 Запуск dev среды...")
	@docker compose up -d
	$(call success,"Dev среда запущена: http://localhost:8000")

test-local: ## Запустить локальную тестовую среду
	$(call log,"🧪 Запуск локальной тестовой среды...")
	@./scripts/test_local.sh start
	$(call success,"Тестовая среда запущена: http://localhost:8001")

# Тестирование
test: ## Запустить все тесты локально
	$(call log,"🧪 Запуск всех тестов...")
	@./scripts/test_local.sh test

test-unit: ## Запустить unit тесты
	$(call log,"⚡ Запуск unit тестов...")
	@./scripts/test_local.sh test-unit

test-int: ## Запустить интеграционные тесты
	$(call log,"🔗 Запуск интеграционных тестов...")
	@./scripts/test_local.sh test-int

test-e2e: ## Запустить E2E тесты
	$(call log,"🎯 Запуск E2E тестов...")
	@./scripts/test_local.sh test-e2e

coverage: ## Запустить тесты с покрытием
	$(call log,"📊 Запуск тестов с покрытием...")
	@./scripts/test_local.sh coverage
	$(call success,"Отчет: htmlcov/index.html")

# Качество кода
lint: ## Проверить качество кода
	$(call log,"🔍 Проверка качества кода...")
	@./scripts/test_local.sh lint

format: ## Форматировать код
	$(call log,"✨ Форматирование кода...")
	@./scripts/test_local.sh format

check: ## Полная проверка (lint + быстрые тесты)
	$(call log,"🔎 Полная проверка кода...")
	@./scripts/test_local.sh check

# Production
prod-test: ## Запустить тесты на production сервере
	$(call log,"🌐 Запуск тестов на production...")
	@ssh root@5.129.224.104 "bot test-fast"

deploy: ## Деплой с полным тестированием
	$(call log,"🚀 Деплой с тестированием...")
	@./scripts/test_and_deploy.sh

# Очистка
clean: ## Очистить все среды и данные
	$(call log,"🧹 Очистка...")
	@docker compose down -v --remove-orphans || true
	@./scripts/test_local.sh clean
	@docker system prune -f
	$(call success,"Очистка завершена")

# Вспомогательные команды
logs: ## Показать логи dev среды
	@docker compose logs -f

test-logs: ## Показать логи тестовой среды
	@./scripts/test_local.sh logs

status: ## Статус всех сред
	$(call log,"📊 Статус dev среды:")
	@docker compose ps || echo "Dev среда не запущена"
	@echo ""
	$(call log,"📊 Статус тестовой среды:")
	@./scripts/test_local.sh status

shell: ## Интерактивная оболочка в тестовом контейнере
	@./scripts/test_local.sh shell

# Быстрые команды для ежедневной работы
quick-test: lint test-unit ## Быстрая проверка перед коммитом
	$(call success,"Быстрая проверка завершена")

full-test: lint test ## Полная проверка перед пушем
	$(call success,"Полная проверка завершена")

# Команды разработки
watch: ## Тесты в режиме наблюдения
	@./scripts/test_local.sh test-watch

db: ## Подключиться к тестовой БД
	@./scripts/test_local.sh db-shell
