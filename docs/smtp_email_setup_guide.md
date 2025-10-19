# 📧 Руководство по настройке SMTP для отправки email уведомлений

## Обзор

Система AI RAG Bot теперь поддерживает отправку email уведомлений для восстановления паролей администраторов. Настройка SMTP опциональна - если не настроена, система будет логировать email в консоль.

## 🔧 Настройка SMTP

### 1. Переменные окружения

Добавьте следующие переменные в ваш `.env` файл:

```env
# Application URL (для ссылок в email)
BASE_URL=https://your-domain.com

# SMTP Settings (для отправки email уведомлений)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Примечание:** `MANAGER_EMAILS` - это отдельная настройка для системных уведомлений менеджерам (например, алерты о превышении лимитов AI расходов). Для восстановления паролей используется email из профиля администратора.

### 1.1. Настройка BASE_URL

Переменная `BASE_URL` определяет домен для ссылок в email уведомлениях:

- **Development:** `BASE_URL=http://127.0.0.1:8000`
- **Production:** `BASE_URL=https://your-domain.com`
- **С поддоменом:** `BASE_URL=https://admin.your-domain.com`

**Важно:** Используйте HTTPS в продакшене для безопасности.

### 2. Популярные SMTP провайдеры

#### Gmail
```env
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Не обычный пароль, а App Password
```

**Важно для Gmail:**
- Включите 2FA в Google аккаунте
- Создайте App Password: Google Account → Security → App passwords
- Используйте App Password, а не обычный пароль

#### Yandex Mail
```env
SMTP_HOST=smtp.yandex.ru
SMTP_USER=your-email@yandex.ru
SMTP_PASSWORD=your-password
```

#### Mail.ru
```env
SMTP_HOST=smtp.mail.ru
SMTP_USER=your-email@mail.ru
SMTP_PASSWORD=your-password
```

#### Корпоративная почта
```env
SMTP_HOST=mail.company.com
SMTP_USER=admin@company.com
SMTP_PASSWORD=your-password
```

### 3. Проверка настройки

После настройки SMTP проверьте работу системы:

1. Перейдите в админ-панель: `http://your-domain/admin/login`
2. Нажмите "Забыли пароль?"
3. Введите email администратора
4. Проверьте получение письма

## 🔍 Диагностика

### Если email не приходят:

1. **Проверьте логи приложения:**
   ```bash
   docker-compose logs app
   ```

2. **Ищите сообщения:**
   - `[EMAIL SIMULATION]` - SMTP не настроен
   - `Email успешно отправлен` - письмо отправлено
   - `Ошибка отправки email` - проблема с SMTP

3. **Проверьте переменные окружения:**
   ```bash
   docker-compose exec app env | grep SMTP
   ```

### Типичные ошибки:

- **"Authentication failed"** - неправильный пароль или App Password
- **"Connection refused"** - неправильный SMTP_HOST или порт заблокирован
- **"SSL/TLS error"** - проблема с шифрованием

## 🛡️ Безопасность

### Рекомендации:

1. **Используйте App Passwords** для Gmail вместо обычных паролей
2. **Не храните пароли** в открытом виде в git
3. **Используйте переменные окружения** для всех настроек
4. **Регулярно меняйте пароли** SMTP аккаунтов

### Безопасное хранение:

```bash
# В production используйте Docker secrets
echo "your-smtp-password" | docker secret create smtp_password -
```

## 📋 Функциональность

### Что работает:

✅ **Восстановление пароля** - отправка ссылки на email  
✅ **Валидация email** - проверка уникальности  
✅ **HTML письма** - красивое оформление  
✅ **Graceful fallback** - логирование если SMTP не настроен  
✅ **Редактирование профиля** - смена email через веб-интерфейс  

### Настройки email:

- **Тема:** "Восстановление пароля - AI RAG Bot"
- **Формат:** HTML + текстовая версия
- **Срок действия:** 1 час
- **Ссылка:** `{BASE_URL}/admin/reset-password?token=...` (использует настройку BASE_URL)

## 🔄 Обновление конфигурации

После изменения SMTP настроек перезапустите приложение:

```bash
# Development
docker-compose restart app

# Production
docker-compose -f docker-compose.prod.yml restart app
```

## 📞 Поддержка

Если возникли проблемы с настройкой SMTP:

1. Проверьте документацию вашего почтового провайдера
2. Убедитесь что порт 587 не заблокирован
3. Проверьте логи приложения для диагностики
4. Обратитесь к администратору системы

---

*Система работает и без SMTP - в этом случае email логируются в консоль для отладки.*
