from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import (
    get_all_services,
    create_service,
    get_service_by_id,
    update_service,
    toggle_service_status
)
from app.config import get_settings
from loguru import logger
from app.routers.web import check_auth

router = APIRouter(tags=["services"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/services-management", response_class=HTMLResponse)
async def services_management_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Страница управления услугами
    """
    # Проверка авторизации
    user_type = check_auth(request)
    if not user_type:
        return RedirectResponse(url="/login", status_code=302)
    
    if user_type != 'admin':
        return RedirectResponse(url="/bookings", status_code=302)
    
    # Получаем все услуги (активные и неактивные)
    services = get_all_services(db, active_only=False)
    
    logger.info(f"Отображение страницы управления услугами. Всего услуг: {len(services)}")
    
    return templates.TemplateResponse(
        "services_management.html",
        {
            "request": request,
            "services": services,
            "user_type": user_type
        }
    )


@router.get("/services-management/list")
async def get_services_list_json(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Получить список всех услуг в JSON (активные и неактивные)
    """
    # Проверка авторизации
    user_type = check_auth(request)
    if not user_type:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if user_type != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    services = get_all_services(db, active_only=False)
    
    return {
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in services
        ]
    }


@router.post("/services/create")
async def create_service_endpoint(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Создать новую услугу
    """
    # Проверка авторизации
    user_type = check_auth(request)
    if not user_type:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if user_type != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Проверка что название не пустое
        if not name or not name.strip():
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Название услуги не может быть пустым"}
            )
        
        service = create_service(db, name.strip())
        
        logger.info(f"Создана новая услуга: {service.name} (ID: {service.id})")
        
        return {
            "status": "success",
            "message": f"Услуга '{service.name}' успешно создана",
            "id": service.id
        }
    except Exception as e:
        logger.error(f"Ошибка при создании услуги: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Ошибка при создании услуги: {str(e)}"}
        )


@router.put("/services/{service_id}")
async def update_service_endpoint(
    request: Request,
    service_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обновить услугу
    """
    # Проверка авторизации
    user_type = check_auth(request)
    if not user_type:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if user_type != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Проверка что название не пустое
        if not name or not name.strip():
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Название услуги не может быть пустым"}
            )
        
        service = update_service(db, service_id, name.strip())
        
        if not service:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Услуга не найдена"}
            )
        
        logger.info(f"Обновлена услуга ID {service_id}: {service.name}")
        
        return {
            "status": "success",
            "message": f"Услуга '{service.name}' успешно обновлена"
        }
    except Exception as e:
        logger.error(f"Ошибка при обновлении услуги: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Ошибка при обновлении услуги: {str(e)}"}
        )


@router.delete("/services/{service_id}")
async def toggle_service_status_endpoint(
    request: Request,
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Переключить статус активности услуги (активировать/деактивировать)
    """
    # Проверка авторизации
    user_type = check_auth(request)
    if not user_type:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if user_type != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        service = toggle_service_status(db, service_id)
        
        if not service:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Услуга не найдена"}
            )
        
        status = "активирована" if service.is_active else "деактивирована"
        logger.info(f"Услуга ID {service_id} {status}")
        
        return {
            "status": "success",
            "message": f"Услуга '{service.name}' успешно {status}",
            "is_active": service.is_active
        }
    except Exception as e:
        logger.error(f"Ошибка при переключении статуса услуги: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Ошибка при переключении статуса услуги: {str(e)}"}
        )
