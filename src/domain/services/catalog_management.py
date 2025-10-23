"""
Сервис управления каталогом товаров с поддержкой blue-green deployment.
Реализует безопасное обновление каталога без простоя системы согласно @vision.md
"""

import asyncio
import logging
import gc
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.database.models import CatalogVersion, AdminUser
from ...infrastructure.search.catalog_service import CatalogSearchService
from ...infrastructure.search.excel_loader import ExcelCatalogLoader
from ...infrastructure.logging.hybrid_logger import hybrid_logger
from ...config.settings import settings

logger = logging.getLogger(__name__)


class CatalogManagementService:
    """
    Сервис управления каталогом с blue-green deployment.
    
    Основные возможности:
    - Загрузка и валидация Excel файлов
    - Blue-green переиндексация без простоя
    - Версионирование каталога
    - Откат к предыдущим версиям
    - Мониторинг прогресса индексации
    """
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.
        
        Args:
            session: Сессия базы данных
        """
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Инициализируем сервисы
        self.catalog_service = CatalogSearchService()
        self.excel_loader = ExcelCatalogLoader()
    
    def _monitor_memory(self) -> float:
        """
        Мониторинг использования памяти.
        
        Returns:
            Потребление памяти в MB
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            return 0.0
    
    async def create_catalog_version(
        self,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        uploaded_by: int,
        status: str = "uploaded"
    ) -> int:
        """
        Создает новую версию каталога в БД.
        
        Args:
            filename: Имя файла на диске
            original_filename: Оригинальное имя файла
            file_path: Путь к файлу
            file_size: Размер файла в байтах
            uploaded_by: ID пользователя, загрузившего файл
            status: Статус версии
            
        Returns:
            ID созданной версии
        """
        version = CatalogVersion(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=uploaded_by,
            status=status,
            is_active=False,
            created_at=datetime.utcnow()
        )
        
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        
        self.logger.info(f"Создана новая версия каталога: {filename} (ID: {version.id})")
        
        return version.id
    
    async def reindex_catalog(self, file_path: str, user_id: int) -> None:
        """
        Выполняет переиндексацию каталога с blue-green deployment.
        
        Алгоритм:
        1. Загружает товары из Excel файла
        2. Создает новую коллекцию в Chroma (blue)
        3. Индексирует товары в новую коллекцию
        4. Атомарно переключает активную коллекцию (green -> blue)
        5. Удаляет старую коллекцию
        
        Args:
            file_path: Путь к Excel файлу
            user_id: ID пользователя, инициировавшего переиндексацию
        """
        start_time = datetime.utcnow()
        
        # Получаем версию каталога из БД
        version = await self._get_version_by_file_path(file_path)
        if not version:
            raise ValueError(f"Версия каталога не найдена для файла: {file_path}")
        
        try:
            # Обновляем статус на "processing"
            await self._update_version_status(
                version.id,
                status="processing",
                started_at=start_time,
                progress=0
            )
            
            # Инициализируем счетчик товаров
            await self._update_version_progress(version.id, 0, "Начало индексации...", 0)
            
            self.logger.info(f"Начинаю переиндексацию каталога: {file_path}")
            
            # Шаг 1: Загружаем товары из Excel с мониторингом памяти
            await self._update_version_progress(version.id, 5, "Загрузка товаров из Excel...", 0)
            
            initial_memory = self._monitor_memory()
            self.logger.info(f"Память перед загрузкой Excel: {initial_memory:.1f} MB")
            
            products = await self.excel_loader.load_products(file_path)
            
            if not products:
                raise ValueError("В файле не найдено товаров для индексации")
            
            loaded_memory = self._monitor_memory()
            self.logger.info(f"Загружено {len(products)} товаров из Excel. Память после загрузки: {loaded_memory:.1f} MB (+{loaded_memory-initial_memory:.1f} MB)")
            
            # Если память выросла слишком сильно - принудительная очистка
            if loaded_memory - initial_memory > 500:  # Если загрузка добавила больше 500MB
                self.logger.warning(f"Большой рост памяти при загрузке Excel: +{loaded_memory-initial_memory:.1f} MB")
                gc.collect()
                await asyncio.sleep(2)
            
            # Шаг 2: Blue-Green индексация
            await self._update_version_progress(version.id, 10, "Создание новой коллекции...", 0)
            
            # Создаем временную коллекцию для новых данных
            temp_collection_name = f"products_catalog_temp_{version.id}"
            
            try:
                # Индексируем товары в временную коллекцию
                await self._index_products_to_collection(
                    products, 
                    temp_collection_name, 
                    version.id
                )
                
                # Шаг 3: Атомарное переключение коллекций
                await self._update_version_progress(version.id, 90, "Переключение активной коллекции...")
                await self._switch_active_collection(temp_collection_name, version_id=version.id)
                
                # Проверяем что переключение действительно завершилось успешно
                final_collection = await self.catalog_service.get_collection(self.catalog_service.COLLECTION_NAME)
                if final_collection is None:
                    raise ValueError("Активная коллекция не найдена после переключения")
                
                final_count = final_collection.count()
                expected_count = len(products)
                
                if final_count != expected_count:
                    raise ValueError(
                        f"Несоответствие количества товаров после переключения: "
                        f"ожидалось {expected_count}, получено {final_count}"
                    )
                
                self.logger.info(f"Переключение коллекции успешно завершено: {final_count} товаров")
                
                # Шаг 4: Обновляем статистику в БД (с повторными попытками при ошибке)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await self._update_version_completion(
                            version.id,
                            products_count=len(products),
                            completed_at=datetime.utcnow()
                        )
                        
                        # Шаг 5: Деактивируем предыдущие версии
                        await self._deactivate_previous_versions(version.id)
                        break  # Успешно обновили
                        
                    except Exception as db_error:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"Ошибка обновления БД (попытка {attempt+1}/{max_retries}): {db_error}")
                            await asyncio.sleep(2)  # Пауза перед повторной попыткой
                        else:
                            # Последняя попытка не удалась - критическая ошибка
                            self.logger.error(
                                f"КРИТИЧЕСКАЯ ОШИБКА: Переключение коллекции завершено, "
                                f"но не удалось обновить статус в БД после {max_retries} попыток: {db_error}"
                            )
                            raise ValueError(
                                f"Коллекция переключена успешно ({final_count} товаров), "
                                f"но не удалось обновить статус в БД: {db_error}"
                            )
                
                self.logger.info(f"Переиндексация завершена успешно: {len(products)} товаров")
                
                await hybrid_logger.info(
                    f"Каталог переиндексирован пользователем {user_id}: "
                    f"{len(products)} товаров за {datetime.utcnow() - start_time}"
                )
                
            except Exception as e:
                # Очищаем временную коллекцию при ошибке
                try:
                    await self.catalog_service.delete_collection(temp_collection_name)
                except:
                    pass  # Игнорируем ошибки очистки
                raise e
                
        except Exception as e:
            # Обновляем статус на "failed"
            await self._update_version_status(
                version.id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.utcnow()
            )
            
            self.logger.error(f"Ошибка переиндексации каталога: {str(e)}")
            raise e
    
    async def _index_products_to_collection(
        self, 
        products: List, 
        collection_name: str, 
        version_id: int
    ) -> None:
        """
        Индексирует товары в указанную коллекцию с отслеживанием прогресса и оптимизацией памяти.
        
        Args:
            products: Список товаров для индексации
            collection_name: Имя коллекции
            version_id: ID версии каталога
        """
        total_products = len(products)
        batch_size = 25  # Очень маленький batch для стабильности на 4GB RAM
        
        # Создаем новую коллекцию
        await self.catalog_service.create_collection(collection_name)
        
        for i in range(0, total_products, batch_size):
            batch = products[i:i + batch_size]
            
            try:
                # Индексируем батч
                await self.catalog_service.index_products_batch(batch, collection_name)
                
                # Обновляем прогресс (10% - 90%)
                progress = 10 + int((i + len(batch)) / total_products * 80)
                message = f"Индексировано {i + len(batch)} из {total_products} товаров..."
                processed_count = i + len(batch)
                
                await self._update_version_progress(version_id, progress, message, processed_count)
                
                # Принудительная очистка памяти каждые 100 товаров
                if (i + len(batch)) % 100 == 0:
                    gc.collect()
                    await asyncio.sleep(1.0)  # Больше времени для освобождения памяти
                    
                    # Мониторинг памяти
                    memory_mb = self._monitor_memory()
                    self.logger.info(f"Обработано {i + len(batch)}/{total_products}, RAM: {memory_mb:.1f} MB")
                    
                    # Если память больше 2.5GB - агрессивная очистка
                    if memory_mb > 2500:
                        self.logger.warning(f"Высокое потребление памяти: {memory_mb:.1f} MB - принудительная очистка")
                        gc.collect()
                        await asyncio.sleep(3)  # Долгая пауза для стабилизации
                
                # Очищаем ссылки на batch
                del batch
                
            except Exception as e:
                self.logger.error(f"Ошибка индексации батча {i}-{i + batch_size}: {e}")
                gc.collect()
                await asyncio.sleep(5)  # Пауза при ошибке
                continue
            
            # Небольшая пауза для снижения нагрузки
            await asyncio.sleep(0.1)
    
    async def _switch_active_collection(self, new_collection_name: str, version_id: Optional[int] = None) -> None:
        """
        Атомарно переключает активную коллекцию.
        
        Args:
            new_collection_name: Имя новой коллекции
        """
        # Получаем текущую активную коллекцию
        old_collection_name = self.catalog_service.COLLECTION_NAME
        
        try:
            async def _report_switch_progress(percent: float, copied: int, total: int) -> None:
                """Обновляет прогресс 90–100% во время переключения коллекции."""
                if version_id is None:
                    return
                # Переводим прогресс копирования (0..100) в 90..100
                bounded = max(0.0, min(100.0, percent))
                progress_value = 90 + int(bounded * 0.10)
                message = f"Переключение коллекции: скопировано {copied} из {total} документов"
                await self._update_version_progress(version_id, progress_value, message)
            # Проверяем, существует ли старая коллекция
            old_exists = await self.catalog_service.collection_exists(old_collection_name)
            
            if old_exists:
                # Если старая коллекция существует, делаем blue-green switch
                backup_collection_name = f"{old_collection_name}_backup_{int(datetime.utcnow().timestamp())}"
                
                # 1. Переименовываем старую коллекцию в backup
                await self.catalog_service.rename_collection(
                    old_collection_name,
                    backup_collection_name,
                    progress_callback=_report_switch_progress
                )
                
                # 2. Переименовываем новую коллекцию в активную
                await self.catalog_service.rename_collection(
                    new_collection_name,
                    old_collection_name,
                    progress_callback=_report_switch_progress
                )
                
                # 3. Удаляем backup коллекцию
                await self.catalog_service.delete_collection(backup_collection_name)
            else:
                # Если старой коллекции нет, просто переименовываем новую в активную
                await self.catalog_service.rename_collection(
                    new_collection_name,
                    old_collection_name,
                    progress_callback=_report_switch_progress
                )
            
        except Exception as e:
            self.logger.error(f"Ошибка переключения коллекции: {e}")
            raise e
    
    async def delete_catalog_version(self, version_id: int) -> None:
        """
        Удаляет версию каталога и связанные файлы.
        
        Args:
            version_id: ID версии для удаления
            
        Raises:
            ValueError: Если версия не найдена или является активной
            Exception: При ошибках удаления файлов или БД
        """
        version = await self._get_version_by_id(version_id)
        if not version:
            raise ValueError(f"Версия каталога с ID {version_id} не найдена")
        
        if version.is_active:
            raise ValueError("Нельзя удалить активную версию каталога")
        
        try:
            # Удаляем файл с диска, если он существует
            if version.file_path and Path(version.file_path).exists():
                Path(version.file_path).unlink()
                self.logger.info(f"Удален файл каталога: {version.file_path}")
            
            # Удаляем коллекцию из ChromaDB, если она существует
            collection_name = f"{self.catalog_service.COLLECTION_NAME}_{version_id}"
            try:
                await self.catalog_service.delete_collection(collection_name)
                self.logger.info(f"Удалена коллекция ChromaDB: {collection_name}")
            except Exception as e:
                # Коллекция может не существовать, это не критично
                self.logger.warning(f"Не удалось удалить коллекцию {collection_name}: {e}")
            
            # Удаляем запись из БД
            await self.session.delete(version)
            await self.session.commit()
            
            self.logger.info(f"Версия каталога {version_id} успешно удалена")
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Ошибка удаления версии каталога {version_id}: {e}")
            raise e

    async def activate_catalog_version(self, version_id: int) -> None:
        """
        Активирует указанную версию каталога (blue-green deployment).
        
        Args:
            version_id: ID версии для активации
            
        Raises:
            ValueError: Если версия не найдена или не готова к активации
            Exception: При ошибках активации
        """
        version = await self._get_version_by_id(version_id)
        if not version:
            raise ValueError(f"Версия каталога с ID {version_id} не найдена")
        
        if version.status not in ["completed", "active"]:
            raise ValueError(f"Версия каталога должна быть в статусе 'completed' для активации. Текущий статус: {version.status}")
        
        try:
            # Деактивируем все текущие активные версии
            await self._deactivate_previous_versions(version_id)
            
            # Активируем выбранную версию
            await self._update_version_status(
                version_id,
                status="active",
                is_active=True
            )
            
            # Переключаем коллекцию в ChromaDB
            collection_name = f"{self.catalog_service.COLLECTION_NAME}_{version_id}"
            
            # Проверяем существование коллекции перед переключением
            if not await self.catalog_service.collection_exists(collection_name):
                raise ValueError(f"Коллекция {collection_name} не существует. Активация невозможна.")
            
            await self._switch_active_collection(collection_name)
            
            self.logger.info(f"Версия каталога {version_id} успешно активирована")
            
        except Exception as e:
            self.logger.error(f"Ошибка активации версии каталога {version_id}: {e}")
            raise e

    # Функция rollback_to_version удалена - функция отката убрана
    
    async def get_current_indexing_status(self) -> Dict[str, Any]:
        """
        Получает текущий статус переиндексации.
        
        Returns:
            Словарь с информацией о статусе
        """
        # Один запрос вместо двух - сначала processing статусы, потом по дате
        stmt = (
            select(CatalogVersion)
            .order_by(
                # Сначала processing статусы (True идет перед False), потом по дате
                CatalogVersion.status == "processing",
                CatalogVersion.created_at.desc()
            )
            .limit(1)
        )
        
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()
        
        if not version:
            return {"status": "idle", "message": "Каталог не загружен"}
        
        # Рассчитываем ожидаемое время завершения только для активных процессов
        estimated_completion = None
        if (version.status == "processing" and 
            version.started_at and version.progress and version.progress > 0):
            # Приводим к одному типу datetime
            now = datetime.utcnow()
            started = version.started_at
            if started.tzinfo is not None:
                # Если started_at с timezone, убираем timezone
                started = started.replace(tzinfo=None)
            
            elapsed = now - started
            total_estimated = elapsed * (100 / version.progress)
            estimated_completion = started + total_estimated
        
        return {
            "status": version.status,
            "progress": version.progress or 0,
            "message": version.progress_message or "",
            "products_count": version.products_count or 0,
            "filename": version.filename,
            "started_at": version.started_at.isoformat() if version.started_at else None,
            "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
            "completed_at": version.completed_at.isoformat() if version.completed_at else None
        }
    
    async def get_version_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает историю версий каталога.
        
        Args:
            limit: Максимальное количество версий
            
        Returns:
            Список версий с информацией
        """
        stmt = (
            select(CatalogVersion, AdminUser.username)
            .outerjoin(AdminUser, CatalogVersion.uploaded_by == AdminUser.id)
            .order_by(CatalogVersion.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        versions = []
        for version, username in rows:
            versions.append({
                "id": version.id,
                "filename": version.filename,
                "file_size": version.file_size,
                "status": version.status,
                "products_count": version.products_count,
                "created_at": version.created_at,
                "uploaded_by_username": username,
                "progress": version.progress,
                "error_message": version.error_message
            })
        
        return versions
    
    async def get_version_by_id(self, version_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает версию каталога по ID.
        
        Args:
            version_id: ID версии
            
        Returns:
            Информация о версии или None
        """
        version = await self._get_version_by_id(version_id)
        if not version:
            return None
        
        return {
            "id": version.id,
            "filename": version.filename,
            "file_path": version.file_path,
            "file_size": version.file_size,
            "file_size_mb": round(version.file_size / 1024 / 1024, 2) if version.file_size else 0,
            "status": version.status,
            "products_count": version.products_count,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "started_at": version.started_at.isoformat() if version.started_at else None,
            "completed_at": version.completed_at.isoformat() if version.completed_at else None,
            "progress": version.progress,
            "error_message": version.error_message
        }
    
    # Приватные методы
    
    async def _get_version_by_file_path(self, file_path: str) -> Optional[CatalogVersion]:
        """Получает версию каталога по пути к файлу."""
        stmt = select(CatalogVersion).where(CatalogVersion.file_path == file_path)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_version_by_id(self, version_id: int) -> Optional[CatalogVersion]:
        """Получает версию каталога по ID."""
        stmt = select(CatalogVersion).where(CatalogVersion.id == version_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _update_version_status(
        self,
        version_id: int,
        status: str,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        indexed_at: Optional[datetime] = None,
        is_active: Optional[bool] = None,
        progress: Optional[int] = None
    ) -> None:
        """Обновляет статус версии каталога."""
        update_data = {"status": status}
        
        if error_message is not None:
            update_data["error_message"] = error_message
        if started_at is not None:
            update_data["started_at"] = started_at
        if completed_at is not None:
            update_data["completed_at"] = completed_at
        if indexed_at is not None:
            update_data["indexed_at"] = indexed_at
        if is_active is not None:
            update_data["is_active"] = is_active
        if progress is not None:
            update_data["progress"] = progress
        
        stmt = (
            update(CatalogVersion)
            .where(CatalogVersion.id == version_id)
            .values(**update_data)
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def _update_version_progress(
        self,
        version_id: int,
        progress: int,
        message: Optional[str] = None,
        products_count: Optional[int] = None
    ) -> None:
        """Обновляет прогресс версии каталога."""
        update_data = {"progress": progress}
        
        if message is not None:
            update_data["progress_message"] = message
        if products_count is not None:
            update_data["products_count"] = products_count
        
        stmt = (
            update(CatalogVersion)
            .where(CatalogVersion.id == version_id)
            .values(**update_data)
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def _update_version_completion(
        self,
        version_id: int,
        products_count: int,
        completed_at: datetime
    ) -> None:
        """Обновляет информацию о завершении индексации."""
        stmt = (
            update(CatalogVersion)
            .where(CatalogVersion.id == version_id)
            .values(
                status="completed",
                products_count=products_count,
                completed_at=completed_at,
                indexed_at=completed_at,  # Время фактического завершения индексации
                progress=100,
                progress_message="Индексация завершена успешно"
            )
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def _deactivate_previous_versions(self, current_version_id: int) -> None:
        """Деактивирует все версии кроме текущей."""
        # Деактивируем все предыдущие версии
        stmt = (
            update(CatalogVersion)
            .where(CatalogVersion.id != current_version_id)
            .values(
                status="completed",
                is_active=False
            )
        )
        
        await self.session.execute(stmt)
        
        # Активируем текущую версию
        stmt = (
            update(CatalogVersion)
            .where(CatalogVersion.id == current_version_id)
            .values(
                status="active",
                is_active=True
            )
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_indexing_status(
        self,
        file_path: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Обновляет статус индексации для внешних вызовов.
        
        Args:
            file_path: Путь к файлу
            status: Новый статус
            error_message: Сообщение об ошибке (если есть)
        """
        version = await self._get_version_by_file_path(file_path)
        if version:
            await self._update_version_status(
                version.id,
                status=status,
                error_message=error_message,
                completed_at=datetime.utcnow() if status in ["completed", "failed"] else None,
                indexed_at=datetime.utcnow() if status == "completed" else None
            )
