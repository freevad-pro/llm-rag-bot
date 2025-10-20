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
    # sentence-transformers использует HuggingFace Hub кэш
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    return cache_dir


def check_model_exists() -> bool:
    """Проверить существование модели в кэше."""
    cache_dir = get_model_cache_path()
    if not cache_dir.exists():
        return False
    
    # Проверяем наличие директории с моделью
    # HuggingFace Hub использует формат: models--org--model
    model_name = settings.embedding_model.replace("/", "--")
    model_dir = cache_dir / f"models--{model_name}"
    
    return model_dir.exists() and any(model_dir.iterdir())


def get_model_size() -> Optional[int]:
    """Получить размер модели в байтах."""
    cache_dir = get_model_cache_path()
    model_name = settings.embedding_model.replace("/", "--")
    model_dir = cache_dir / f"models--{model_name}"
    
    if not model_dir.exists():
        return None
    
    total_size = 0
    for file in model_dir.rglob("*"):
        if file.is_file():
            total_size += file.stat().st_size
    
    return total_size


async def _download_model_task():
    """Фоновая задача для скачивания модели через HuggingFace Hub с симуляцией прогресса."""
    global _download_status
    
    try:
        _download_status["is_downloading"] = True
        _download_status["progress"] = 5
        _download_status["message"] = "Начинаю загрузку модели..."
        _download_status["error"] = None
        
        await hybrid_logger.info(f"Начало загрузки модели {settings.embedding_model}")
        await asyncio.sleep(0.5)
        
        _download_status["progress"] = 10
        _download_status["message"] = "Подключение к HuggingFace Hub..."
        await asyncio.sleep(0.5)
        
        # Импортируем huggingface_hub для надёжной загрузки
        from huggingface_hub import snapshot_download
        import os
        
        _download_status["progress"] = 15
        _download_status["message"] = "Настройка загрузки..."
        
        # Увеличиваем таймауты для работы с большими файлами
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '300'  # 5 минут на файл
        
        _download_status["progress"] = 20
        _download_status["message"] = "Загрузка файлов модели (~470 MB)..."
        await asyncio.sleep(0.5)
        
        # Определяем путь для кэша
        cache_dir = get_model_cache_path()
        
        # Создаём задачу для симуляции прогресса во время реальной загрузки
        async def simulate_progress():
            """Симуляция прогресса во время долгой загрузки."""
            # Прогресс от 25% до 75% за ~15 минут (максимальное время загрузки)
            for progress in range(25, 76):
                if not _download_status["is_downloading"]:
                    break
                _download_status["progress"] = progress
                if progress < 40:
                    _download_status["message"] = f"Скачивание модели... {progress}% (это займёт 5-15 минут)"
                elif progress < 60:
                    _download_status["message"] = f"Загрузка продолжается... {progress}% (осталось ~10 минут)"
                else:
                    _download_status["message"] = f"Почти готово... {progress}% (осталось ~5 минут)"
                await asyncio.sleep(12)  # ~51 шаг * 12 сек = ~10 минут на весь диапазон
        
        # Запускаем симуляцию прогресса параллельно
        progress_task = asyncio.create_task(simulate_progress())
        
        _download_status["progress"] = 25
        _download_status["message"] = "Скачивание модели... 25% (это может занять 5-15 минут)"
        
        # Загружаем модель через snapshot_download для надёжности
        # Он умеет работать с редиректами, CDN, докачкой при обрыве
        try:
            local_dir = await asyncio.to_thread(
                snapshot_download,
                repo_id=settings.embedding_model,
                cache_dir=str(cache_dir.parent),  # HF Hub сам создаст нужную структуру
                resume_download=True,  # Докачка при обрыве
                max_workers=4,  # Параллельная загрузка файлов
                local_files_only=False
            )
            
            # Останавливаем симуляцию прогресса
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            _download_status["progress"] = 80
            _download_status["message"] = "Модель скачана, инициализация..."
            await asyncio.sleep(0.5)
            
        except Exception as download_error:
            # Останавливаем симуляцию при ошибке
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            await hybrid_logger.error(f"Ошибка snapshot_download: {download_error}")
            raise RuntimeError(f"Не удалось скачать модель с HuggingFace: {download_error}")
        
        _download_status["progress"] = 85
        _download_status["message"] = "Проверка работоспособности модели..."
        await asyncio.sleep(0.5)
        
        # Проверяем что модель работает через SentenceTransformer
        from sentence_transformers import SentenceTransformer
        
        model = await asyncio.to_thread(
            SentenceTransformer,
            settings.embedding_model,
            cache_folder=str(cache_dir.parent)
        )
        
        _download_status["progress"] = 92
        _download_status["message"] = "Тестирование эмбеддингов..."
        await asyncio.sleep(0.5)
        
        # Тестовая генерация эмбеддинга
        test_embedding = await asyncio.to_thread(
            model.encode,
            ["тест"]
        )
        
        if test_embedding is None or len(test_embedding) == 0:
            raise ValueError("Модель не возвращает эмбеддинги")
        
        _download_status["progress"] = 98
        _download_status["message"] = "Финализация..."
        await asyncio.sleep(0.5)
        
        _download_status["progress"] = 100
        _download_status["message"] = "✅ Модель успешно загружена и готова к использованию!"
        _download_status["is_downloading"] = False
        
        await hybrid_logger.info(
            f"Модель {settings.embedding_model} успешно загружена. "
            f"Путь: {local_dir if 'local_dir' in locals() else 'cache'}"
        )
        
    except Exception as e:
        _download_status["is_downloading"] = False
        _download_status["progress"] = 0
        _download_status["error"] = str(e)
        _download_status["message"] = f"❌ Ошибка загрузки: {str(e)}"
        
        await hybrid_logger.error(
            f"Ошибка загрузки модели {settings.embedding_model}: {e}",
            exc_info=True
        )


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
    Сбросить статус загрузки модели.
    
    Важно: Фоновая загрузка через snapshot_download продолжит работу,
    но UI статус будет сброшен для возможности повторной попытки.
    Благодаря resume_download=True повторная попытка продолжит с места остановки.
    """
    global _download_status
    
    if not _download_status["is_downloading"]:
        return JSONResponse({
            "success": False,
            "message": "Загрузка не выполняется"
        }, status_code=400)
    
    _download_status["is_downloading"] = False
    _download_status["progress"] = 0
    _download_status["message"] = "Статус сброшен пользователем (фоновая загрузка продолжается)"
    _download_status["error"] = None
    
    await hybrid_logger.warning(
        f"Пользователь {current_user.username} сбросил статус загрузки модели. "
        f"Фоновая загрузка продолжится."
    )
    
    return JSONResponse({
        "success": True,
        "message": "Статус сброшен"
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

