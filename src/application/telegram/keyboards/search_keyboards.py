"""
Клавиатуры для поиска товаров в Telegram боте.
Реализует интерфейс взаимодействия с результатами поиска.
"""

from typing import Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ....domain.entities.product import SearchResult


class SearchKeyboardBuilder:
    """
    Строитель клавиатур для поиска товаров.
    """
    
    @staticmethod
    def _sanitize_callback_data(text: str) -> str:
        """
        Очищает текст для использования в callback_data.
        Telegram принимает только ASCII символы и максимум 64 байта.
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст для callback_data
        """
        # Заменяем проблемные символы
        replacements = {
            '(': '_',
            ')': '_',
            ',': '_',
            ' ': '_',
            '-': '_',
            '/': '_',
            '\\': '_',
            ':': '_',
            ';': '_',
            '"': '_',
            "'": '_',
            '&': '_',
            '%': '_',
            '#': '_',
            '@': '_',
            '!': '_',
            '?': '_',
            '+': '_',
            '=': '_',
            '[': '_',
            ']': '_',
            '{': '_',
            '}': '_',
            '|': '_',
            '~': '_',
            '`': '_',
            '^': '_',
            '*': '_',
            '$': '_'
        }
        
        # Применяем замены
        sanitized = text
        for old, new in replacements.items():
            sanitized = sanitized.replace(old, new)
        
        # Убираем множественные подчеркивания
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # Убираем подчеркивания в начале и конце
        sanitized = sanitized.strip('_')
        
        # Ограничиваем длину до 50 символов (оставляем место для префикса)
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized
    
    @staticmethod
    def build_categories_keyboard(categories: list[str], current_page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с категориями товаров.
        
        Args:
            categories: Список категорий
            current_page: Текущая страница
            page_size: Количество категорий на странице
            
        Returns:
            Inline клавиатура с категориями
        """
        builder = InlineKeyboardBuilder()
        
        # Пагинация категорий
        start_idx = current_page * page_size
        end_idx = start_idx + page_size
        page_categories = categories[start_idx:end_idx]
        
        # Добавляем кнопки категорий (по 2 в ряд)
        for i in range(0, len(page_categories), 2):
            row_buttons = []
            
            # Первая кнопка в ряду
            category = page_categories[i]
            category_index = start_idx + i
            row_buttons.append(
                InlineKeyboardButton(
                    text=category[:25] + "..." if len(category) > 25 else category,
                    callback_data=f"search_category:{category_index}"
                )
            )
            
            # Вторая кнопка в ряду (если есть)
            if i + 1 < len(page_categories):
                category = page_categories[i + 1]
                category_index = start_idx + i + 1
                row_buttons.append(
                    InlineKeyboardButton(
                        text=category[:25] + "..." if len(category) > 25 else category,
                        callback_data=f"search_category:{category_index}"
                    )
                )
            
            builder.row(*row_buttons)
        
        # Навигация между страницами
        nav_buttons = []
        total_pages = (len(categories) + page_size - 1) // page_size
        
        if current_page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"categories_page:{current_page - 1}"
                )
            )
        
        if current_page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Далее", 
                    callback_data=f"categories_page:{current_page + 1}"
                )
            )
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        # Кнопка "Все категории" и "Назад к поиску"
        builder.row(
            InlineKeyboardButton(
                text="🔍 Поиск без фильтра",
                callback_data="search_all_categories"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def build_search_results_keyboard(
        search_results: list[SearchResult], 
        current_page: int = 0,
        page_size: int = 5,
        query: str = "",
        category: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с результатами поиска.
        
        Args:
            search_results: Результаты поиска
            current_page: Текущая страница
            page_size: Количество результатов на странице
            query: Поисковый запрос (для навигации)
            category: Категория фильтра (для навигации)
            
        Returns:
            Inline клавиатура с результатами
        """
        builder = InlineKeyboardBuilder()
        
        # Пагинация результатов
        start_idx = current_page * page_size
        end_idx = start_idx + page_size
        page_results = search_results[start_idx:end_idx]
        
        # Добавляем кнопки товаров
        for i, result in enumerate(page_results, 1):
            product = result.product
            
            # Формируем текст кнопки: Артикул | Название
            if product.article:
                # Если есть артикул, показываем его
                button_text = f"{product.article} | {product.product_name}"
                # Обрезаем если слишком длинное
                if len(button_text) > 60:
                    # Сохраняем артикул полностью, обрезаем название
                    max_name_length = 60 - len(product.article) - 5  # 5 для " | ..."
                    if max_name_length > 0:
                        button_text = f"{product.article} | {product.product_name[:max_name_length]}..."
                    else:
                        button_text = button_text[:57] + "..."
            else:
                # Если нет артикула, просто название
                button_text = f"{i}. {product.product_name}"
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"product_details:{product.id}"
                )
            )
        
        # Навигация между страницами результатов
        nav_buttons = []
        total_pages = (len(search_results) + page_size - 1) // page_size
        
        if current_page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"search_results_page:{current_page - 1}:{query}:{category or ''}"
                )
            )
        
        if current_page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Далее",
                    callback_data=f"search_results_page:{current_page + 1}:{query}:{category or ''}"
                )
            )
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        # Дополнительные действия
        action_buttons = []
        
        # Кнопка "Новый поиск"
        action_buttons.append(
            InlineKeyboardButton(
                text="🔍 Новый поиск",
                callback_data="new_search"
            )
        )
        
        # Кнопка "Связаться с менеджером"
        action_buttons.append(
            InlineKeyboardButton(
                text="👨‍💼 Менеджер",
                callback_data="contact_manager"
            )
        )
        
        builder.row(*action_buttons)
        
        # Кнопка "Главное меню"
        builder.row(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def build_product_details_keyboard(
        product_id: str,
        has_photo: bool = False,
        has_page_url: bool = False
    ) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для детальной информации о товаре.
        
        Args:
            product_id: ID товара
            has_photo: Есть ли фото товара
            has_page_url: Есть ли ссылка на страницу товара
            
        Returns:
            Inline клавиатура с действиями
        """
        builder = InlineKeyboardBuilder()
        
        # Первый ряд - просмотр медиа
        media_buttons = []
        
        if has_photo:
            media_buttons.append(
                InlineKeyboardButton(
                    text="📷 Фото",
                    callback_data=f"product_photo:{product_id}"
                )
            )
        
        if has_page_url:
            media_buttons.append(
                InlineKeyboardButton(
                    text="🌐 На сайте",
                    callback_data=f"product_page:{product_id}"
                )
            )
        
        if media_buttons:
            builder.row(*media_buttons)
        
        # Второй ряд - действия
        builder.row(
            InlineKeyboardButton(
                text="💼 Заказать",
                callback_data=f"order_product:{product_id}"
            ),
            InlineKeyboardButton(
                text="❓ Вопрос",
                callback_data=f"ask_about_product:{product_id}"
            )
        )
        
        # Третий ряд - навигация
        builder.row(
            InlineKeyboardButton(
                text="⬅️ К результатам",
                callback_data="back_to_search_results"
            ),
            InlineKeyboardButton(
                text="🔍 Новый поиск",
                callback_data="new_search"
            )
        )
        
        # Четвертый ряд - главное меню
        builder.row(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def build_search_start_keyboard() -> InlineKeyboardMarkup:
        """
        Создает стартовую клавиатуру для поиска.
        
        Returns:
            Inline клавиатура с опциями поиска
        """
        builder = InlineKeyboardBuilder()
        
        # Основные опции поиска
        builder.row(
            InlineKeyboardButton(
                text="🔍 Поиск по названию",
                callback_data="search_by_name"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="📂 Поиск по категориям",
                callback_data="search_by_categories"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🆔 Поиск по артикулу",
                callback_data="search_by_article"
            )
        )
        
        # Дополнительные действия
        builder.row(
            InlineKeyboardButton(
                text="👨‍💼 Связаться с менеджером",
                callback_data="contact_manager"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def build_no_results_keyboard(query: str) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для случая, когда ничего не найдено.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Inline клавиатура с опциями
        """
        builder = InlineKeyboardBuilder()
        
        # Предложения действий
        builder.row(
            InlineKeyboardButton(
                text="🔍 Изменить запрос",
                callback_data="new_search"
            ),
            InlineKeyboardButton(
                text="📂 По категориям",
                callback_data="search_by_categories"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="👨‍💼 Спросить менеджера",
                callback_data="contact_manager"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def back_to_search_menu() -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с кнопкой возврата к меню поиска.
        
        Returns:
            Inline клавиатура с кнопкой "Назад к поиску"
        """
        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(
                text="🔍 Назад к поиску",
                callback_data="new_search"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()


# Готовые клавиатуры для частого использования

def get_main_search_keyboard() -> InlineKeyboardMarkup:
    """Возвращает основную клавиатуру поиска."""
    return SearchKeyboardBuilder.build_search_start_keyboard()


def get_contact_manager_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для связи с менеджером."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📞 Оставить контакты",
            callback_data="leave_contacts"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Продолжить поиск",
            callback_data="new_search"
        ),
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()
