"""
Сервис управления услугами компании
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from ..entities.company_service import CompanyService
from ..entities.service_category import ServiceCategory
from ...infrastructure.database.models import CompanyService as CompanyServiceModel, ServiceCategory as ServiceCategoryModel
from ...infrastructure.logging.hybrid_logger import hybrid_logger


class CompanyServiceManagementService:
    """Сервис для управления услугами компании"""
    
    def _model_to_entity(self, service_model: CompanyServiceModel) -> CompanyService:
        """Конвертирует модель БД в domain entity"""
        category = None
        if service_model.category_rel:
            category = ServiceCategory(
                id=service_model.category_rel.id,
                name=service_model.category_rel.name,
                display_name=service_model.category_rel.display_name,
                description=service_model.category_rel.description,
                color=service_model.category_rel.color,
                icon=service_model.category_rel.icon,
                is_active=service_model.category_rel.is_active,
                sort_order=service_model.category_rel.sort_order,
                created_at=service_model.category_rel.created_at,
                updated_at=service_model.category_rel.updated_at
            )
                
        return CompanyService(
            id=service_model.id,
            name=service_model.name,
            description=service_model.description,
            category_id=service_model.category_id,
            category=category,
            keywords=service_model.keywords,
            price_info=service_model.price_info,
            is_active=service_model.is_active,
            sort_order=service_model.sort_order,
            created_at=service_model.created_at,
            updated_at=service_model.updated_at
        )
    
    async def get_all_services(
        self, 
        session: AsyncSession, 
        active_only: bool = False,
        search_term: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> List[CompanyService]:
        """Получить все услуги с фильтрацией"""
        stmt = select(CompanyServiceModel).options(selectinload(CompanyServiceModel.category_rel))
        
        # Фильтры
        conditions = []
        
        if active_only:
            conditions.append(CompanyServiceModel.is_active == True)
            
        if search_term:
            search_pattern = f"%{search_term}%"
            conditions.append(
                or_(
                    CompanyServiceModel.name.ilike(search_pattern),
                    CompanyServiceModel.description.ilike(search_pattern),
                    CompanyServiceModel.keywords.ilike(search_pattern),
                    CompanyServiceModel.price_info.ilike(search_pattern)
                )
            )
            
        if category_id:
            conditions.append(CompanyServiceModel.category_id == category_id)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
            
        # Сортировка: активные сначала, потом по порядку, потом по имени
        stmt = stmt.order_by(
            CompanyServiceModel.is_active.desc(),
            CompanyServiceModel.sort_order.asc(),
            CompanyServiceModel.name.asc()
        )
        
        result = await session.execute(stmt)
        service_models = result.scalars().all()
        
        return [self._model_to_entity(service) for service in service_models]
    
    async def get_service_by_id(self, session: AsyncSession, service_id: int) -> Optional[CompanyService]:
        """Получить услугу по ID"""
        stmt = select(CompanyServiceModel).options(selectinload(CompanyServiceModel.category_rel)).where(CompanyServiceModel.id == service_id)
        result = await session.execute(stmt)
        service_model = result.scalar_one_or_none()
        
        if not service_model:
            return None
            
        return self._model_to_entity(service_model)
    
    async def create_service(
        self, 
        session: AsyncSession, 
        name: str,
        description: str,
        created_by: int,
        category_id: Optional[int] = None,
        keywords: Optional[str] = None,
        price_info: Optional[str] = None,
        is_active: bool = True,
        sort_order: int = 0
    ) -> Optional[CompanyService]:
        """Создать новую услугу"""
        try:
            service_model = CompanyServiceModel(
                name=name.strip(),
                description=description.strip(),
                category_id=category_id,
                keywords=keywords.strip() if keywords else None,
                price_info=price_info.strip() if price_info else None,
                is_active=is_active,
                sort_order=sort_order
            )
            
            session.add(service_model)
            await session.commit()
            await session.refresh(service_model)
            
            await hybrid_logger.info(f"Создана новая услуга '{name}' пользователем {created_by}")
            
            return self._model_to_entity(service_model)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка создания услуги '{name}': {e}")
            await session.rollback()
            return None
    
    async def update_service(
        self, 
        session: AsyncSession, 
        service_id: int,
        updated_by: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        keywords: Optional[str] = None,
        price_info: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_order: Optional[int] = None
    ) -> bool:
        """Обновить услугу"""
        try:
            # Подготавливаем данные для обновления
            update_data = {}
            
            if name is not None:
                update_data['name'] = name.strip()
            if description is not None:
                update_data['description'] = description.strip()
            if category_id is not None:
                update_data['category_id'] = category_id
            if keywords is not None:
                update_data['keywords'] = keywords.strip() if keywords else None
            if price_info is not None:
                update_data['price_info'] = price_info.strip() if price_info else None
            if is_active is not None:
                update_data['is_active'] = is_active
            if sort_order is not None:
                update_data['sort_order'] = sort_order
            
            if not update_data:
                return True  # Нечего обновлять
            
            # Обновляем услугу
            stmt = (
                update(CompanyServiceModel)
                .where(CompanyServiceModel.id == service_id)
                .values(**update_data)
            )
            await session.execute(stmt)
            await session.commit()
            
            await hybrid_logger.info(f"Обновлена услуга ID {service_id} пользователем {updated_by}")
            
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка обновления услуги {service_id}: {e}")
            await session.rollback()
            return False
    
    async def delete_service(self, session: AsyncSession, service_id: int, deleted_by: int) -> bool:
        """Удалить услугу"""
        try:
            stmt = delete(CompanyServiceModel).where(CompanyServiceModel.id == service_id)
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                await hybrid_logger.info(f"Удалена услуга ID {service_id} пользователем {deleted_by}")
                return True
            else:
                return False
                
        except Exception as e:
            await hybrid_logger.error(f"Ошибка удаления услуги {service_id}: {e}")
            await session.rollback()
            return False
    
    async def toggle_service_status(self, session: AsyncSession, service_id: int, toggled_by: int) -> bool:
        """Переключить статус активности услуги"""
        try:
            # Получаем текущий статус
            service = await self.get_service_by_id(session, service_id)
            if not service:
                return False
            
            # Переключаем статус
            new_status = not service.is_active
            success = await self.update_service(
                session, service_id, toggled_by, is_active=new_status
            )
            
            if success:
                status_text = "активирована" if new_status else "деактивирована"
                await hybrid_logger.info(f"Услуга '{service.name}' {status_text} пользователем {toggled_by}")
            
            return success
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка переключения статуса услуги {service_id}: {e}")
            return False
    
    async def get_services_by_category(self, session: AsyncSession, category: ServiceCategory) -> List[CompanyService]:
        """Получить услуги по категории"""
        return await self.get_all_services(session, active_only=True, category=category)
    
    async def search_services(self, session: AsyncSession, search_term: str) -> List[CompanyService]:
        """Поиск услуг по термину"""
        return await self.get_all_services(session, active_only=True, search_term=search_term)


# Экземпляр сервиса
company_service_management = CompanyServiceManagementService()
