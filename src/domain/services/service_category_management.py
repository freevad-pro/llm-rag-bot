"""
Сервис управления категориями услуг
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from ..entities.service_category import ServiceCategory
from ...infrastructure.database.models import ServiceCategory as ServiceCategoryModel
from ...infrastructure.logging.hybrid_logger import hybrid_logger


class ServiceCategoryManagementService:
    """Сервис для управления категориями услуг"""
    
    def _model_to_entity(self, category_model: ServiceCategoryModel) -> ServiceCategory:
        """Конвертирует модель БД в domain entity"""
        return ServiceCategory(
            id=category_model.id,
            name=category_model.name,
            display_name=category_model.display_name,
            description=category_model.description,
            color=category_model.color,
            icon=category_model.icon,
            is_active=category_model.is_active,
            sort_order=category_model.sort_order,
            created_at=category_model.created_at,
            updated_at=category_model.updated_at
        )
    
    async def get_all_categories(
        self, 
        session: AsyncSession, 
        active_only: bool = False,
        search_term: Optional[str] = None
    ) -> List[ServiceCategory]:
        """Получить все категории с фильтрацией"""
        stmt = select(ServiceCategoryModel)
        
        # Фильтры
        conditions = []
        
        if active_only:
            conditions.append(ServiceCategoryModel.is_active == True)
            
        if search_term:
            search_pattern = f"%{search_term}%"
            conditions.append(
                or_(
                    ServiceCategoryModel.name.ilike(search_pattern),
                    ServiceCategoryModel.display_name.ilike(search_pattern),
                    ServiceCategoryModel.description.ilike(search_pattern)
                )
            )
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
            
        # Сортировка: активные сначала, потом по порядку, потом по имени
        stmt = stmt.order_by(
            ServiceCategoryModel.is_active.desc(),
            ServiceCategoryModel.sort_order.asc(),
            ServiceCategoryModel.display_name.asc()
        )
        
        result = await session.execute(stmt)
        category_models = result.scalars().all()
        
        return [self._model_to_entity(category) for category in category_models]
    
    async def get_category_by_id(self, session: AsyncSession, category_id: int) -> Optional[ServiceCategory]:
        """Получить категорию по ID"""
        stmt = select(ServiceCategoryModel).where(ServiceCategoryModel.id == category_id)
        result = await session.execute(stmt)
        category_model = result.scalar_one_or_none()
        
        if not category_model:
            return None
            
        return self._model_to_entity(category_model)
    
    async def get_category_by_name(self, session: AsyncSession, name: str) -> Optional[ServiceCategory]:
        """Получить категорию по техническому имени"""
        stmt = select(ServiceCategoryModel).where(ServiceCategoryModel.name == name)
        result = await session.execute(stmt)
        category_model = result.scalar_one_or_none()
        
        if not category_model:
            return None
            
        return self._model_to_entity(category_model)
    
    async def create_category(
        self, 
        session: AsyncSession, 
        name: str,
        display_name: str,
        created_by: int,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: bool = True,
        sort_order: int = 0
    ) -> Optional[ServiceCategory]:
        """Создать новую категорию"""
        try:
            # Проверяем уникальность имени
            existing = await self.get_category_by_name(session, name)
            if existing:
                await hybrid_logger.warning(f"Категория с именем '{name}' уже существует")
                return None
            
            category_model = ServiceCategoryModel(
                name=name.strip(),
                display_name=display_name.strip(),
                description=description.strip() if description else None,
                color=color.strip() if color else None,
                icon=icon.strip() if icon else None,
                is_active=is_active,
                sort_order=sort_order
            )
            
            session.add(category_model)
            await session.commit()
            await session.refresh(category_model)
            
            await hybrid_logger.info(f"Создана новая категория '{display_name}' ({name}) пользователем {created_by}")
            
            return self._model_to_entity(category_model)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка создания категории '{name}': {e}")
            await session.rollback()
            return None
    
    async def update_category(
        self, 
        session: AsyncSession, 
        category_id: int,
        updated_by: int,
        name: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_order: Optional[int] = None
    ) -> bool:
        """Обновить категорию"""
        try:
            # Подготавливаем данные для обновления
            update_data = {}
            
            if name is not None:
                # Проверяем уникальность нового имени
                existing = await self.get_category_by_name(session, name)
                if existing and existing.id != category_id:
                    await hybrid_logger.warning(f"Категория с именем '{name}' уже существует")
                    return False
                update_data['name'] = name.strip()
                
            if display_name is not None:
                update_data['display_name'] = display_name.strip()
            if description is not None:
                update_data['description'] = description.strip() if description else None
            if color is not None:
                update_data['color'] = color.strip() if color else None
            if icon is not None:
                update_data['icon'] = icon.strip() if icon else None
            if is_active is not None:
                update_data['is_active'] = is_active
            if sort_order is not None:
                update_data['sort_order'] = sort_order
            
            if not update_data:
                return True  # Нечего обновлять
            
            # Обновляем категорию
            stmt = (
                update(ServiceCategoryModel)
                .where(ServiceCategoryModel.id == category_id)
                .values(**update_data)
            )
            await session.execute(stmt)
            await session.commit()
            
            await hybrid_logger.info(f"Обновлена категория ID {category_id} пользователем {updated_by}")
            
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка обновления категории {category_id}: {e}")
            await session.rollback()
            return False
    
    async def delete_category(self, session: AsyncSession, category_id: int, deleted_by: int) -> bool:
        """Удалить категорию (только если нет связанных услуг)"""
        try:
            # Проверяем, есть ли услуги с этой категорией
            from ...infrastructure.database.models import CompanyService
            stmt = select(CompanyService).where(CompanyService.category_id == category_id)
            result = await session.execute(stmt)
            linked_services = result.scalars().all()
            
            if linked_services:
                await hybrid_logger.warning(f"Нельзя удалить категорию {category_id}: есть {len(linked_services)} связанных услуг")
                return False
            
            stmt = delete(ServiceCategoryModel).where(ServiceCategoryModel.id == category_id)
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                await hybrid_logger.info(f"Удалена категория ID {category_id} пользователем {deleted_by}")
                return True
            else:
                return False
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка удаления категории {category_id}: {e}")
            await session.rollback()
            return False
    
    async def toggle_category_status(self, session: AsyncSession, category_id: int, toggled_by: int) -> bool:
        """Переключить статус активности категории"""
        try:
            # Получаем текущий статус
            category = await self.get_category_by_id(session, category_id)
            if not category:
                return False
            
            # Переключаем статус
            new_status = not category.is_active
            success = await self.update_category(
                session, category_id, toggled_by, is_active=new_status
            )
            
            if success:
                status_text = "активирована" if new_status else "деактивирована"
                await hybrid_logger.info(f"Категория '{category.display_name}' {status_text} пользователем {toggled_by}")
            
            return success
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка переключения статуса категории {category_id}: {e}")
            return False
    
    async def initialize_default_categories(self, session: AsyncSession) -> None:
        """Инициализирует дефолтные категории, если их нет"""
        default_categories = [
            {
                "name": "development",
                "display_name": "Разработка",
                "description": "Создание программного обеспечения, веб-приложений и мобильных приложений",
                "color": "#007bff",
                "icon": "code-slash",
                "sort_order": 1
            },
            {
                "name": "consulting",
                "display_name": "Консалтинг",
                "description": "Консультационные услуги по IT и бизнес-процессам",
                "color": "#28a745",
                "icon": "people",
                "sort_order": 2
            },
            {
                "name": "support",
                "display_name": "Поддержка",
                "description": "Техническая поддержка и сопровождение проектов",
                "color": "#ffc107",
                "icon": "headset",
                "sort_order": 3
            },
            {
                "name": "design",
                "display_name": "Дизайн",
                "description": "UI/UX дизайн, графический дизайн и брендинг",
                "color": "#e83e8c",
                "icon": "palette",
                "sort_order": 4
            },
            {
                "name": "analytics",
                "display_name": "Аналитика",
                "description": "Анализ данных, бизнес-аналитика и отчетность",
                "color": "#17a2b8",
                "icon": "graph-up",
                "sort_order": 5
            },
            {
                "name": "marketing",
                "display_name": "Маркетинг",
                "description": "Цифровой маркетинг, SEO и продвижение",
                "color": "#fd7e14",
                "icon": "megaphone",
                "sort_order": 6
            },
            {
                "name": "training",
                "display_name": "Обучение",
                "description": "Образовательные программы и тренинги",
                "color": "#6f42c1",
                "icon": "book",
                "sort_order": 7
            },
            {
                "name": "integration",
                "display_name": "Интеграция",
                "description": "Интеграция систем и API",
                "color": "#20c997",
                "icon": "diagram-3",
                "sort_order": 8
            },
            {
                "name": "other",
                "display_name": "Прочее",
                "description": "Другие услуги",
                "color": "#6c757d",
                "icon": "gear",
                "sort_order": 99
            }
        ]
        
        for category_data in default_categories:
            existing = await self.get_category_by_name(session, category_data["name"])
            if not existing:
                await self.create_category(
                    session,
                    category_data["name"],
                    category_data["display_name"],
                    0,  # Системный пользователь
                    category_data["description"],
                    category_data["color"],
                    category_data["icon"],
                    True,
                    category_data["sort_order"]
                )


# Экземпляр сервиса
service_category_management = ServiceCategoryManagementService()







