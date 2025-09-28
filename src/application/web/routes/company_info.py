"""
Роуты для управления информацией о компании
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional

from ....infrastructure.database.connection import get_session
from .admin import get_current_admin_user, require_admin_user
from ....infrastructure.database.models import CompanyInfo as CompanyInfoModel, AdminUser
from ....domain.entities.company_info import CompanyInfo, CompanyInfoUpload
from ....infrastructure.utils.docx_parser import DocxParser
from ....presentation.template_config import templates

router = APIRouter(prefix="/admin/company-info", tags=["company-info"])


@router.get("/", response_class=HTMLResponse)
async def company_info_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Страница управления информацией о компании
    """
    # Получаем текущую активную версию
    current_query = select(CompanyInfoModel).where(
        CompanyInfoModel.is_active == True
    ).order_by(desc(CompanyInfoModel.created_at))
    
    current_result = await session.execute(current_query)
    current_info = current_result.scalar_one_or_none()
    
    # Получаем историю версий (последние 10)
    history_query = select(CompanyInfoModel).order_by(
        desc(CompanyInfoModel.created_at)
    ).limit(10)
    
    history_result = await session.execute(history_query)
    history = history_result.scalars().all()
    
    return templates.TemplateResponse(
        "admin/company_info.html",
        {
            "request": request,
            "current_user": current_user,
            "current_info": current_info,
            "history": history,
            "page_title": "Информация о компании"
        }
    )


@router.post("/upload")
async def upload_company_info(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Загрузка файла с информацией о компании
    """
    # Проверяем размер файла (максимум 2MB)
    if file.size and file.size > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Размер файла не должен превышать 2MB"
        )
    
    # Проверяем расширение файла
    if not file.filename or not file.filename.lower().endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Поддерживается только формат DOCX"
        )
    
    try:
        # Читаем содержимое файла
        file_content = await file.read()
        
        # Валидируем DOCX файл
        if not DocxParser.validate_docx(file_content):
            raise HTTPException(
                status_code=400,
                detail="Файл не является валидным DOCX документом"
            )
        
        # Извлекаем текст
        extracted_text = DocxParser.extract_text(file_content)
        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="Не удалось извлечь текст из документа"
            )
        
        # Деактивируем предыдущие версии
        await session.execute(
            CompanyInfoModel.__table__.update().values(is_active=False)
        )
        
        # Получаем следующий номер версии
        last_version_query = select(CompanyInfoModel.version).order_by(
            desc(CompanyInfoModel.version)
        ).limit(1)
        
        last_version_result = await session.execute(last_version_query)
        last_version = last_version_result.scalar_one_or_none()
        next_version = (last_version or 0) + 1
        
        # Создаем новую запись
        new_info = CompanyInfoModel(
            filename=f"company_info_v{next_version}.docx",
            original_filename=file.filename,
            file_size=len(file_content),
            file_type="DOCX",
            content=extracted_text,
            version=next_version,
            is_active=True,
            uploaded_by=current_user.id
        )
        
        session.add(new_info)
        await session.commit()
        
        return RedirectResponse(
            url="/admin/company-info?success=uploaded",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке файла: {str(e)}"
        )


@router.get("/preview/{info_id}")
async def preview_company_info(
    info_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Предварительный просмотр информации о компании
    """
    query = select(CompanyInfoModel).where(CompanyInfoModel.id == info_id)
    result = await session.execute(query)
    info = result.scalar_one_or_none()
    
    if not info:
        raise HTTPException(status_code=404, detail="Информация не найдена")
    
    return {
        "id": info.id,
        "filename": info.original_filename,
        "version": info.version,
        "file_size": info.file_size,
        "content": info.content,
        "is_active": info.is_active,
        "created_at": info.created_at.isoformat() if info.created_at else None
    }




@router.delete("/delete/{info_id}")
async def delete_company_info(
    info_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Удаление версии информации о компании
    """
    
    query = select(CompanyInfoModel).where(CompanyInfoModel.id == info_id)
    result = await session.execute(query)
    info = result.scalar_one_or_none()
    
    if not info:
        raise HTTPException(status_code=404, detail="Информация не найдена")
    
    # Нельзя удалить активную версию
    if info.is_active:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить активную версию"
        )
    
    await session.delete(info)
    await session.commit()
    
    return {"success": True}


@router.post("/delete-old-versions")
async def delete_old_versions(
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_admin_user)
):
    """
    Удаление всех неактивных версий информации о компании
    """
    # Получаем все неактивные версии
    query = select(CompanyInfoModel).where(CompanyInfoModel.is_active == False)
    result = await session.execute(query)
    old_versions = result.scalars().all()
    
    if not old_versions:
        return RedirectResponse(
            url="/admin/company-info?info=no_old_versions",
            status_code=303
        )
    
    # Удаляем все неактивные версии
    for version in old_versions:
        await session.delete(version)
    
    await session.commit()
    
    return RedirectResponse(
        url="/admin/company-info?success=old_versions_deleted",
        status_code=303
    )
