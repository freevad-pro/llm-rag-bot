"""
Роуты для управления моделью эмбеддингов.
Позволяет скачивать, проверять статус и удалять модель sentence-transformers.
"""
import os
import shutil
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse

from .admin import require_admin_only
from ....domain.entities.admin_user import AdminUser
from ....infrastructure.logging.hybrid_logger import hybrid_logger
from ....presentation.template_config import templates
from ....config.settings import settings

model_router = APIRouter(prefix="/admin/model", tags=["model"])

# Глобальная переменная для отслеживания статуса загрузки
_download_status = {
    "is_downloading": False,
    "progress": 0,
    "message": "",
    "error": None
}


def get_model_cache_path() -> Path:
    """Получить путь к кэшу модели."""
    # sentence-transformers кэширует в ~/.cache/torch/sentence_transformers/
    cache_dir = Path.home() / ".cache" / "torch" / "sentence_transformers"
    return cache_dir


def check_model_exists() -> bool:
    """Проверить существование модели в кэше."""
    cache_dir = get_model_cache_path()
    if not cache_dir.exists():
        return False
    
    # Проверяем наличие директории с моделью
    model_name = settings.embedding_model.replace("/", "_")
    model_dir = cache_dir / model_name
    
    return model_dir.exists() and any(model_dir.iterdir())


def get_model_size() -> Optional[int]:
    """Получить размер модели в байтах."""
    cache_dir = get_model_cache_path()
    model_name = settings.embedding_model.replace("/", "_")
    model_dir = cache_dir / model_name
    
    if not model_dir.exists():
        return None
    
    total_size = 0
    for file in model_dir.rglob("*"):
        if file.is_file():
            total_size += file.stat().st_size
    
    return total_size


async def _download_model_task():
    """Фоновая задача для скачивания модели."""
    global _download_status
    
    try:
        _download_status["is_downloading"] = True
        _download_status["progress"] = 0
        _download_status["message"] = "Начинаю загрузку модели..."
        _download_status["error"] = None
        
        await hybrid_logger.info(f"Начало загрузки модели {settings.embedding_model}")
        
        # Импортируем в фоновой задаче чтобы не блокировать основной поток
        from sentence_transformers import SentenceTransformer
        
        _download_status["progress"] = 10
        _download_status["message"] = "Подключение к HuggingFace..."
        
        # Загружаем модель - это автоматически скачает и закэширует её
        model = SentenceTransformer(settings.embedding_model)
        
        _download_status["progress"] = 90
        _download_status["message"] = "Проверка модели..."
        
        # Проверяем что модель работает
        test_embedding = model.encode(["тест"])
        
        if test_embedding is None or len(test_embedding) == 0:
            raise ValueError("Модель не возвращает эмбеддинги")
        
        _download_status["progress"] = 100
        _download_status["message"] = "Модель успешно загружена и готова к использованию!"
        _download_status["is_downloading"] = False
        
        await hybrid_logger.info(f"Модель {settings.embedding_model} успешно загружена")
        
    except Exception as e:
        _download_status["is_downloading"] = False
        _download_status["progress"] = 0
        _download_status["error"] = str(e)
        _download_status["message"] = f"Ошибка загрузки: {str(e)}"
        
        await hybrid_logger.error(f"Ошибка загрузки модели {settings.embedding_model}: {e}")


@model_router.get("/", response_class=HTMLResponse)
async def model_management_page(
    request: Request,
    current_user: AdminUser = Depends(require_admin_only)
):
    """
    Страница управления моделью эмбеддингов.
    Доступна только администраторам.
    """
    model_exists = check_model_exists()
    model_size = get_model_size() if model_exists else None
    
    context = {
        "request": request,
        "current_user": current_user,
        "page_title": "Управление моделью эмбеддингов",
        "model_name": settings.embedding_model,
        "model_provider": settings.embedding_provider,
        "model_exists": model_exists,
        "model_size_mb": round(model_size / 1024 / 1024, 2) if model_size else None,
        "is_downloading": _download_status["is_downloading"]
    }
    
    return templates.TemplateResponse("admin/model_management.html", context)


@model_router.get("/status")
async def get_model_status(
    current_user: AdminUser = Depends(require_admin_only)
):
    """
    API endpoint для получения статуса модели.
    """
    model_exists = check_model_exists()
    model_size = get_model_size() if model_exists else None
    
    return JSONResponse({
        "model_name": settings.embedding_model,
        "model_provider": settings.embedding_provider,
        "model_exists": model_exists,
        "model_size_bytes": model_size,
        "model_size_mb": round(model_size / 1024 / 1024, 2) if model_size else None,
        "cache_path": str(get_model_cache_path()),
        "is_downloading": _download_status["is_downloading"],
        "download_progress": _download_status["progress"],
        "download_message": _download_status["message"],
        "download_error": _download_status["error"]
    })


@model_router.post("/download")
async def download_model(
    background_tasks: BackgroundTasks,
    current_user: AdminUser = Depends(require_admin_only)
):
    """
    Запустить загрузку модели в фоновом режиме.
    """
    global _download_status
    
    # Проверяем что загрузка уже не идёт
    if _download_status["is_downloading"]:
        return JSONResponse({
            "success": False,
            "message": "Загрузка уже выполняется"
        }, status_code=400)
    
    # Запускаем фоновую задачу
    background_tasks.add_task(_download_model_task)
    
    await hybrid_logger.info(f"Пользователь {current_user.username} запустил загрузку модели {settings.embedding_model}")
    
    return JSONResponse({
        "success": True,
        "message": "Загрузка модели начата"
    })


@model_router.post("/cancel")
async def cancel_download(
    current_user: AdminUser = Depends(require_admin_only)
):
    """
    Отменить текущую загрузку модели.
    Примечание: Физически остановить загрузку невозможно,
    но мы сбросим статус для возможности повторной попытки.
    """
    global _download_status
    
    if not _download_status["is_downloading"]:
        return JSONResponse({
            "success": False,
            "message": "Загрузка не выполняется"
        }, status_code=400)
    
    _download_status["is_downloading"] = False
    _download_status["progress"] = 0
    _download_status["message"] = "Загрузка отменена пользователем"
    _download_status["error"] = "Отменено"
    
    await hybrid_logger.warning(f"Пользователь {current_user.username} отменил загрузку модели")
    
    return JSONResponse({
        "success": True,
        "message": "Загрузка отменена"
    })


@model_router.delete("/")
async def delete_model(
    current_user: AdminUser = Depends(require_admin_only)
):
    """
    Удалить модель из кэша.
    """
    global _download_status
    
    # Проверяем что загрузка не идёт
    if _download_status["is_downloading"]:
        return JSONResponse({
            "success": False,
            "message": "Нельзя удалить модель во время загрузки"
        }, status_code=400)
    
    cache_dir = get_model_cache_path()
    model_name = settings.embedding_model.replace("/", "_")
    model_dir = cache_dir / model_name
    
    if not model_dir.exists():
        return JSONResponse({
            "success": False,
            "message": "Модель не найдена"
        }, status_code=404)
    
    try:
        # Удаляем директорию с моделью
        shutil.rmtree(model_dir)
        
        await hybrid_logger.info(f"Пользователь {current_user.username} удалил модель {settings.embedding_model}")
        
        return JSONResponse({
            "success": True,
            "message": "Модель успешно удалена"
        })
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка удаления модели: {e}")
        
        return JSONResponse({
            "success": False,
            "message": f"Ошибка удаления: {str(e)}"
        }, status_code=500)

