"""
Дефолтные настройки классификации запросов для KeTai Consulting ИИ-бота.
Готовые к использованию в ClassificationSettingsService.
"""

# Дефолтные настройки классификации
DEFAULT_CLASSIFICATION_SETTINGS = {
    "enable_fast_classification": True,
    "enable_llm_classification": True,
    
    # Конкретные товары и оборудование
    "specific_products": [
        "сверло", "drill", "bit", "керн", "core",
        "болт", "винт", "гайка", "шайба", "nut", "bolt", "screw", "washer",
        "подшипник", "bearing", "фильтр", "filter", "масло", "oil",
        "ремень", "belt", "насос", "pump", "двигатель", "motor", "engine",
        "компрессор", "compressor", "клапан", "valve", "шланг", "hose",
        "кабель", "cable", "wire", "провод", "провода",
        "резистор", "resistor", "конденсатор", "capacitor", "транзистор", "transistor",
        "микросхема", "chip", "плата", "board", "разъем", "connector",
        "датчик", "sensor", "реле", "relay", "контроллер", "controller"
    ],
    
    # Общие слова для товаров
    "product_keywords": [
        "товар", "product", "оборудование", "equipment", 
        "запчасть", "part", "spare", "деталь", "detail",
        "артикул", "article", "sku", "модель", "model",
        "компонент", "component", "изделие", "item"
    ],
    
    # Фразы о наличии товаров
    "availability_phrases": [
        "есть ли у вас", "do you have", "продаете ли", "do you sell",
        "найдется ли", "can be found", "имеется ли", "is available",
        "у вас есть", "you have", "в наличии", "in stock",
        "есть в наличии", "available in stock", "можно ли купить", 
        "can I buy", "можно ли заказать", "can I order",
        "есть ли возможность", "is it possible", "реализуете ли", "do you supply",
        "есть ли", "is there", "имеется", "available", "доступно", "accessible",
        "можно найти", "can find", "можно получить", "can get",
        "продается", "sold", "предлагается", "offered", "предлагаете", "do you offer"
    ],
    
    # Слова поиска
    "search_words": [
        "найти", "find", "искать", "search", "нужен", "need", 
        "требуется", "required", "looking for", "ищу", "поиск",
        "подобрать", "select", "выбрать", "choose"
    ],
    
    # Ключевые слова для контакта с менеджером
    "contact_keywords": [
        "менеджер", "manager", "связаться", "contact", 
        "позвонить", "call", "заказать", "order", 
        "купить", "buy", "цена", "price", "консультация", 
        "consultation", "помощь менеджера", "manager help",
        "связаться с менеджером", "contact manager",
        "нужна помощь", "need help", "консультант", "consultant"
    ],
    
    # Ключевые слова для вопросов о компании
    "company_keywords": [
        "компания", "company", "о вас", "about you", 
        "адрес", "address", "контакты", "contacts", 
        "история", "history", "местоположение", "location",
        "офис", "office", "где находитесь", "where are you located",
        "информация о компании", "company information"
    ]
}
