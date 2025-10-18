/**
 * Основные JavaScript функции для админ-панели KeTai Consulting
 */

// Глобальные переменные
window.AdminPanel = {
    notifications: [],
    config: {
        notificationTimeout: 5000,
        ajaxTimeout: 10000,
    }
};

/**
 * Система уведомлений
 */
class NotificationManager {
    constructor() {
        this.container = document.getElementById('notifications');
        if (!this.container) {
            console.warn('Контейнер для уведомлений не найден');
        }
    }

    show(message, type = 'info', timeout = 5000) {
        if (!this.container) return;

        const id = 'notification-' + Date.now();
        const icons = {
            success: 'bi-check-circle',
            error: 'bi-exclamation-triangle',
            warning: 'bi-exclamation-triangle',
            info: 'bi-info-circle'
        };

        const alert = document.createElement('div');
        alert.id = id;
        alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alert.setAttribute('role', 'alert');
        alert.innerHTML = `
            <i class="bi ${icons[type] || icons.info}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        this.container.appendChild(alert);

        // Автоматическое удаление
        if (timeout > 0) {
            setTimeout(() => {
                this.remove(id);
            }, timeout);
        }

        return id;
    }

    remove(id) {
        const alert = document.getElementById(id);
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }

    success(message, timeout = 5000) {
        return this.show(message, 'success', timeout);
    }

    error(message, timeout = 8000) {
        return this.show(message, 'error', timeout);
    }

    warning(message, timeout = 6000) {
        return this.show(message, 'warning', timeout);
    }

    info(message, timeout = 5000) {
        return this.show(message, 'info', timeout);
    }
}

/**
 * AJAX утилиты
 */
class AjaxManager {
    constructor() {
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
    }

    async request(url, options = {}) {
        const config = {
            method: 'GET',
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        // Добавляем CSRF токен если есть
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            config.headers['X-CSRF-Token'] = csrfToken.getAttribute('content');
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('AJAX Error:', error);
            throw error;
        }
    }

    async get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    }

    async post(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }
}

/**
 * Утилиты для работы с формами
 */
class FormUtils {
    static serialize(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Если ключ уже существует, делаем массив
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }

    static validate(form) {
        const errors = [];
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                errors.push(`Поле "${field.name || field.id}" обязательно для заполнения`);
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        // Проверка email
        const emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            if (field.value && !this.isValidEmail(field.value)) {
                errors.push(`Некорректный email: ${field.value}`);
                field.classList.add('is-invalid');
            }
        });

        return errors;
    }

    static isValidEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }

    static showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        // Удаляем предыдущие сообщения об ошибках
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }

        // Добавляем новое сообщение
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    static clearErrors(form) {
        const invalidFields = form.querySelectorAll('.is-invalid');
        invalidFields.forEach(field => {
            field.classList.remove('is-invalid');
        });

        const errorMessages = form.querySelectorAll('.invalid-feedback');
        errorMessages.forEach(msg => msg.remove());
    }
}

/**
 * Загрузчик файлов с drag & drop
 */
class FileUploader {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            maxSize: 100 * 1024 * 1024, // 100MB
            allowedTypes: [],
            multiple: false,
            ...options
        };
        
        this.init();
    }

    init() {
        this.element.addEventListener('dragover', this.handleDragOver.bind(this));
        this.element.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.element.addEventListener('drop', this.handleDrop.bind(this));
        
        // Добавляем input если его нет
        if (!this.element.querySelector('input[type="file"]')) {
            const input = document.createElement('input');
            input.type = 'file';
            input.style.display = 'none';
            input.multiple = this.options.multiple;
            if (this.options.allowedTypes.length > 0) {
                input.accept = this.options.allowedTypes.join(',');
            }
            this.element.appendChild(input);
            
            this.element.addEventListener('click', () => input.click());
            input.addEventListener('change', (e) => this.handleFiles(e.target.files));
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        this.element.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.element.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.element.classList.remove('dragover');
        this.handleFiles(e.dataTransfer.files);
    }

    handleFiles(files) {
        const fileArray = Array.from(files);
        const validFiles = fileArray.filter(file => this.validateFile(file));
        
        if (validFiles.length > 0) {
            this.options.onFiles && this.options.onFiles(validFiles);
        }
    }

    validateFile(file) {
        // Проверка размера
        if (file.size > this.options.maxSize) {
            notifications.error(`Файл ${file.name} слишком большой. Максимальный размер: ${this.formatFileSize(this.options.maxSize)}`);
            return false;
        }

        // Проверка типа
        if (this.options.allowedTypes.length > 0) {
            const fileType = '.' + file.name.split('.').pop().toLowerCase();
            if (!this.options.allowedTypes.includes(fileType)) {
                notifications.error(`Файл ${file.name} имеет недопустимый тип. Разрешены: ${this.options.allowedTypes.join(', ')}`);
                return false;
            }
        }

        return true;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

/**
 * Утилиты для работы с модальными окнами
 */
class ModalUtils {
    static async show(modalId, data = {}) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`Модальное окно ${modalId} не найдено`);
            return;
        }

        // Заполняем данными если есть
        Object.keys(data).forEach(key => {
            const field = modal.querySelector(`[name="${key}"], #${key}`);
            if (field) {
                if (field.type === 'checkbox') {
                    field.checked = !!data[key];
                } else {
                    field.value = data[key] || '';
                }
            }
        });

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        return bsModal;
    }

    static hide(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }
}

// Инициализация глобальных объектов
window.notifications = new NotificationManager();
window.ajax = new AjaxManager();
window.FormUtils = FormUtils;
window.FileUploader = FileUploader;
window.ModalUtils = ModalUtils;

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Инициализация Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Автоматическое закрытие алертов через время
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        if (!alert.querySelector('.btn-close')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });

    // Подтверждение удаления
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn-delete, .delete-btn') || e.target.closest('.btn-delete, .delete-btn')) {
            if (!confirm('Вы уверены, что хотите удалить этот элемент?')) {
                e.preventDefault();
                return false;
            }
        }
    });

    // Обработка форм с HTMX
    document.addEventListener('htmx:responseError', function(e) {
        notifications.error('Ошибка при выполнении запроса: ' + e.detail.xhr.statusText);
    });

    document.addEventListener('htmx:sendError', function(e) {
        notifications.error('Ошибка соединения с сервером');
    });

    console.log('Admin Panel JS initialized');
});

/**
 * Функция для переключения sidebar на мобильных устройствах
 */
window.toggleSidebar = function() {
    const sidebar = document.getElementById('sidebarMenu');
    if (!sidebar) return;
    
    sidebar.classList.toggle('show');
    
    // Обновляем overlay если он есть
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) {
        if (sidebar.classList.contains('show')) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    }
};

/**
 * Автоматически скрываем sidebar при клике вне его на мобильных
 */
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebarMenu');
    if (!sidebar) return;
    
    const toggleBtn = event.target.closest('.btn[onclick*="toggleSidebar"]');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (!sidebar.contains(event.target) && !toggleBtn && window.innerWidth <= 767) {
        sidebar.classList.remove('show');
        if (overlay) overlay.classList.remove('show');
    }
});

