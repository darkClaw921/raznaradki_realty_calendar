from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from loguru import logger

from app.database import get_db
from app.schemas import MonthlyPlanCreate, MonthlyPlanUpdate, MonthlyPlanResponse
from app import crud
from app.routers.web import check_auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/plans-management", response_class=HTMLResponse)
async def plans_management_page(request: Request, db: Session = Depends(get_db)):
    user_type = check_auth(request)
    if not user_type:
        return RedirectResponse(url="/login", status_code=302)
    if user_type != 'admin':
        return RedirectResponse(url="/bookings", status_code=302)

    all_plans = crud.get_all_plans(db)

    return templates.TemplateResponse("plans.html", {
        "request": request,
        "plans": all_plans,
        "user_type": user_type
    })

@router.post("/plans/create")
async def create_monthly_plan_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    start_date: str = Form(...),
    end_date: str = Form(...),
    target_amount: str = Form(...)
):
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    if user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )

    try:
        start_date_obj = date.fromisoformat(start_date)
        end_date_obj = date.fromisoformat(end_date)
        target_amount_float = float(target_amount)

        plan_data = MonthlyPlanCreate(
            start_date=start_date_obj,
            end_date=end_date_obj,
            target_amount=target_amount_float
        )

        plan = crud.create_monthly_plan(db, plan_data)

        return JSONResponse(content={
            "status": "success",
            "message": "План создан",
            "id": plan.id
        })
    except Exception as e:
        logger.error(f"Ошибка при создании плана: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.get("/plans/list")
async def list_monthly_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    if user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )

    plans = crud.get_all_plans(db)
    result = []
    for plan in plans:
        plan_data = MonthlyPlanResponse.from_orm(plan).model_dump()
        if isinstance(plan_data.get("start_date"), date):
            plan_data["start_date"] = plan_data["start_date"].isoformat()
        if isinstance(plan_data.get("end_date"), date):
            plan_data["end_date"] = plan_data["end_date"].isoformat()
        if isinstance(plan_data.get("created_at"), date):
            plan_data["created_at"] = plan_data["created_at"].isoformat()
        if isinstance(plan_data.get("updated_at"), date):
            plan_data["updated_at"] = plan_data["updated_at"].isoformat()
        result.append(plan_data)

    return JSONResponse(content={"plans": result})

@router.put("/plans/{plan_id}")
async def update_monthly_plan_endpoint(
    request: Request,
    plan_id: int,
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    target_amount: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    if user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )

    try:
        update_data = {}

        if start_date is not None:
            update_data["start_date"] = date.fromisoformat(start_date)
        if end_date is not None:
            update_data["end_date"] = date.fromisoformat(end_date)
        if target_amount is not None:
            update_data["target_amount"] = float(target_amount)

        if not update_data:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Нет данных для обновления"}
            )

        plan_update = MonthlyPlanUpdate(**update_data)
        plan = crud.update_monthly_plan(db, plan_id, plan_update)

        if not plan:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "План не найден"}
            )

        return JSONResponse(content={
            "status": "success",
            "message": "План обновлен"
        })
    except Exception as e:
        logger.error(f"Ошибка при обновлении плана: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.delete("/plans/{plan_id}")
async def delete_monthly_plan_endpoint(
    request: Request,
    plan_id: int,
    db: Session = Depends(get_db)
):
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    if user_type != 'admin':
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Доступ запрещен"}
        )

    success = crud.delete_monthly_plan(db, plan_id)

    if not success:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "План не найден"}
        )

    return JSONResponse(content={
        "status": "success",
        "message": "План удален"
    })