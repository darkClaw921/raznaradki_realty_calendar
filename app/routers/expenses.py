from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from loguru import logger

from app.database import get_db
from app.schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from app.config import get_settings
from app import crud
from app.routers.web import check_auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

@router.get("/expenses", response_class=HTMLResponse)
async def expenses_page(
    request: Request,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    apartment_title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Страница с таблицей расходов
    """
    user_type = check_auth(request)
    if not user_type:
        return RedirectResponse(url="/login", status_code=302)
    
    # Парсинг дат фильтра
    filter_date_from_obj = None
    filter_date_to_obj = None
    
    if filter_date_from:
        try:
            filter_date_from_obj = date.fromisoformat(filter_date_from)
        except ValueError:
            logger.warning(f"Некорректная дата начала: {filter_date_from}")
    
    if filter_date_to:
        try:
            filter_date_to_obj = date.fromisoformat(filter_date_to)
        except ValueError:
            logger.warning(f"Некорректная дата окончания: {filter_date_to}")
    
    # Получаем расходы
    expenses_list = crud.get_expenses(
        db,
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj,
        apartment_title=apartment_title
    )
    
    # Получаем уникальные объекты для dropdown (оптимизированный запрос)
    unique_apartments = crud.get_unique_apartments(db)
    
    # Подсчет общей суммы расходов
    total_expenses = sum(float(expense.amount) for expense in expenses_list)
    
    return templates.TemplateResponse("expenses.html", {
        "request": request,
        "expenses": expenses_list,
        "unique_apartments": unique_apartments,
        "filter_date_from": filter_date_from,
        "filter_date_to": filter_date_to,
        "apartment_title": apartment_title,
        "total_expenses": total_expenses,
        "user_type": user_type
    })

@router.post("/expenses/create")
async def create_expense(
    request: Request,
    db: Session = Depends(get_db),
    apartment_title: Optional[str] = Form(None),
    expense_date: str = Form(...),
    amount: str = Form(...),
    category: Optional[str] = Form(None),
    comment: Optional[str] = Form(None)
):
    """
    Создать новый расход
    """
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    
    try:
        amount_float = float(amount)
        
        # Парсинг даты
        expense_date_obj = date.fromisoformat(expense_date)
        
        # Создание расхода
        expense_data = ExpenseCreate(
            apartment_title=apartment_title if apartment_title and apartment_title.strip() else None,
            expense_date=expense_date_obj,
            amount=amount_float,
            category=category if category and category.strip() else None,
            comment=comment if comment and comment.strip() else None
        )
        
        expense = crud.create_expense(db, expense_data)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Расход создан",
            "id": expense.id
        })
    
    except Exception as e:
        logger.error(f"Ошибка при создании расхода: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.get("/expenses/list")
async def list_expenses(
    request: Request,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    apartment_title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получить список расходов в JSON формате
    """
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    
    # Парсинг дат фильтра
    filter_date_from_obj = None
    filter_date_to_obj = None
    
    if filter_date_from:
        try:
            filter_date_from_obj = date.fromisoformat(filter_date_from)
        except ValueError:
            pass
    
    if filter_date_to:
        try:
            filter_date_to_obj = date.fromisoformat(filter_date_to)
        except ValueError:
            pass
    
    expenses = crud.get_expenses(
        db, 
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj,
        apartment_title=apartment_title
    )
    
    result = []
    for expense in expenses:
        result.append({
            "id": expense.id,
            "apartment_title": expense.apartment_title,
            "expense_date": expense.expense_date.isoformat(),
            "amount": float(expense.amount),
            "category": expense.category,
            "comment": expense.comment
        })
    
    return JSONResponse(content={"expenses": result})

@router.put("/expenses/{expense_id}")
async def update_expense_endpoint(
    request: Request,
    expense_id: int,
    apartment_title: Optional[str] = Form(None),
    expense_date: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),
    category: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Обновить расход
    """
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    
    try:
        # Подготовка данных для обновления
        update_data = {}
        
        if apartment_title is not None:
            update_data["apartment_title"] = apartment_title if apartment_title.strip() else None
        
        if expense_date is not None:
            update_data["expense_date"] = date.fromisoformat(expense_date)
        
        if amount is not None:
            update_data["amount"] = amount
        
        if category is not None:
            update_data["category"] = category if category.strip() else None
        
        if comment is not None:
            update_data["comment"] = comment if comment.strip() else None
        
        expense_update = ExpenseUpdate(**update_data)
        expense = crud.update_expense(db, expense_id, expense_update)
        
        if not expense:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Расход не найден"}
            )
        
        return JSONResponse(content={
            "status": "success",
            "message": "Расход обновлен"
        })
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении расхода: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.delete("/expenses/{expense_id}")
async def delete_expense_endpoint(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db)
):
    """
    Удалить расход
    """
    user_type = check_auth(request)
    if not user_type:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    
    success = crud.delete_expense(db, expense_id)
    
    if not success:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Расход не найден"}
        )
    
    return JSONResponse(content={
        "status": "success",
        "message": "Расход удален"
    })