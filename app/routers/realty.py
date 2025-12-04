from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.database import get_db
from app.schemas import RealtyUpdate
from app.config import get_settings
from app import crud
from app.routers.web import check_auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

@router.get("/realty-management", response_class=HTMLResponse)
async def realty_management_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Страница управления объектами недвижимости
    """
    user_type = check_auth(request)
    if not user_type:
        return RedirectResponse(url="/login", status_code=302)
    
    if user_type != 'admin':
        return RedirectResponse(url="/bookings", status_code=302)
    
    # Синхронизируем объекты из всех источников (bookings, payments, expenses)
    # Это гарантирует, что все объекты из поступлений будут в таблице realty
    crud.sync_realty_from_all_sources(db)
    
    realty_objects = crud.get_all_realty(db)
    
    return templates.TemplateResponse("realty.html", {
        "request": request,
        "realty_objects": realty_objects,
        "user_type": user_type
    })

@router.get("/realty/list")
async def list_realty(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Получить список всех объектов в JSON
    """
    user_type = check_auth(request)
    if not user_type or user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )
    
    realty_objects = crud.get_all_realty(db)
    
    result = []
    for obj in realty_objects:
        result.append({
            "id": obj.id,
            "name": obj.name,
            "is_active": obj.is_active,
            "created_at": obj.created_at.isoformat(),
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None
        })
    
    return JSONResponse(content={"realty_objects": result})

@router.put("/realty/{realty_id}")
async def update_realty_endpoint(
    request: Request,
    realty_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обновить название объекта
    """
    user_type = check_auth(request)
    if not user_type or user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )
    
    if not name or not name.strip():
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Название не может быть пустым"}
        )
    
    try:
        # Получаем старое название перед обновлением
        old_realty = crud.get_realty_by_id(db, realty_id)
        if not old_realty:
             return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Объект не найден"}
            )
        old_name = old_realty.name
        
        realty_update = RealtyUpdate(name=name)
        realty = crud.update_realty(db, realty_id, realty_update)
        
        if not realty:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Объект не найден"}
            )
            
        # Если имя изменилось, обновляем его во всех бронированиях
        if old_name != name:
            crud.update_bookings_apartment_title(db, old_name, name)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Объект обновлен"
        })
    except Exception as e:
        logger.error(f"Ошибка при обновлении объекта: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.delete("/realty/{realty_id}")
async def toggle_realty_status(
    request: Request,
    realty_id: int,
    db: Session = Depends(get_db)
):
    """
    Переключить статус активности объекта
    """
    user_type = check_auth(request)
    if not user_type or user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )
    
    realty = crud.get_realty_by_id(db, realty_id)
    if not realty:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Объект не найден"}
        )
    
    # Переключаем статус
    new_status = not realty.is_active
    realty_update = RealtyUpdate(is_active=new_status)
    updated_realty = crud.update_realty(db, realty_id, realty_update)
    
    return JSONResponse(content={
        "status": "success",
        "message": "Статус обновлен",
        "is_active": updated_realty.is_active
    })
