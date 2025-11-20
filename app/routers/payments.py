from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, time
from loguru import logger

from app.database import get_db
from app.schemas import PaymentCreate, PaymentUpdate, PaymentResponse
from app.config import get_settings
from app import crud
from app.models import MonthlyPlan
from app.routers.web import check_auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

@router.get("/payments", response_class=HTMLResponse)
async def payments_page(
    request: Request,
    filter_date: Optional[str] = None,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    apartment_title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Страница с таблицей поступлений денег
    """
    user_type = check_auth(request)
    if not user_type:
        return RedirectResponse(url="/login", status_code=302)
    
    if user_type != 'admin':
        return RedirectResponse(url="/bookings", status_code=302)
    
    # Парсинг дат фильтра
    filter_date_obj = None
    filter_date_from_obj = None
    filter_date_to_obj = None
    
    if filter_date:
        try:
            filter_date_obj = date.fromisoformat(filter_date)
        except ValueError:
            logger.warning(f"Некорректная дата фильтра: {filter_date}")
    
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
    
    # Получаем поступления из таблицы payments для таблицы (фильтр по receipt_date)
    payments_list = crud.get_payments(
        db,
        filter_date=filter_date_obj,
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj,
        apartment_title=apartment_title
    )
    
    # Получаем услуги из booking_services как поступления (фильтр по begin_date)
    booking_services_as_payments = crud.get_booking_services_as_payments(
        db,
        filter_date=filter_date_obj,
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj,
        apartment_title=apartment_title
    )
    
    # Объединяем поступления: сначала из payments, потом из booking_services
    combined_payments = []
    
    # Добавляем реальные поступления
    for p in payments_list:
        combined_payments.append({
            'id': p.id,
            'booking_id': p.booking_id,
            'booking_service_id': p.booking_service_id,
            'apartment_title': p.apartment_title,
            'receipt_date': p.receipt_date,
            'receipt_time': p.receipt_time,
            'amount': float(p.amount),
            'operation_type': p.operation_type,
            'income_category': p.income_category,
            'comment': p.comment,
            'booking_service': p.booking_service if hasattr(p, 'booking_service') else None,
            'is_from_booking_service': False
        })
    
    # Добавляем услуги из booking_services
    combined_payments.extend(booking_services_as_payments)
    
    # Сортируем по дате (новые первыми)
    combined_payments.sort(key=lambda x: x['receipt_date'], reverse=True)
    
    # Получаем бронирования с услугами для формы
    bookings_with_services = crud.get_bookings_with_services(db, filter_date=filter_date_from_obj)
    
    # Получаем уникальные объекты для dropdown (оптимизированный запрос)
    unique_apartments = crud.get_unique_apartments(db)
    
    # Находим активный план для периода фильтра
    active_plan = None
    total_plan = 0.0
    if filter_date_from_obj and filter_date_to_obj:
        active_plan = crud.get_active_plan_for_period(db, filter_date_from_obj, filter_date_to_obj)
        if active_plan:
            total_plan = float(active_plan.target_amount)
    elif filter_date_obj:
        # Для одной даты используем тот же день как период
        active_plan = crud.get_active_plan_for_period(db, filter_date_obj, filter_date_obj)
        if active_plan:
            total_plan = float(active_plan.target_amount)
    
    # Расчет факта реального заселения: сумма amount всех бронирований с begin_date в диапазоне фильтра
    bookings_for_fact: List = []
    if filter_date_obj:
        bookings_for_fact = crud.get_bookings_by_begin_date(
            db,
            filter_date=filter_date_obj,
            apartment_title=apartment_title
        )
    elif filter_date_from_obj or filter_date_to_obj:
        bookings_for_fact = crud.get_bookings_by_begin_date(
            db,
            filter_date_from=filter_date_from_obj,
            filter_date_to=filter_date_to_obj,
            apartment_title=apartment_title
        )
    
    total_fact = sum(float(booking.amount or 0.0) for booking in bookings_for_fact)
    
    # Группировка по объектам с учётом дублей
    grouped_fact_bookings = []
    total_fact_prepayment = 0.0
    total_fact_payment = 0.0
    if bookings_for_fact:
        groups = {}
        for booking in bookings_for_fact:
            title = (booking.apartment_title or '').strip()
            if not title:
                title = 'Без названия'
            normalized = title.replace(' ДУБЛЬ', '').replace(' Дубль', '').strip()
            groups.setdefault(normalized, {
                "title": normalized,
                "items": [],
                "total_amount": 0.0,
                "total_prepayment": 0.0,
                "total_payment": 0.0
            })
            groups[normalized]["items"].append(booking)
            groups[normalized]["total_amount"] += float(booking.amount or 0.0)
            groups[normalized]["total_prepayment"] += float(booking.prepayment or 0.0)
            groups[normalized]["total_payment"] += float(booking.payment or 0.0)
        
        grouped_fact_bookings = list(groups.values())
        grouped_fact_bookings.sort(key=lambda g: g["title"])
        for group in grouped_fact_bookings:
            group["items"].sort(key=lambda b: (b.apartment_title or '').upper())
            total_fact_prepayment += group["total_prepayment"]
            total_fact_payment += group["total_payment"]
    total_real_payments = sum(float(payment.amount or 0.0) for payment in payments_list)
    total_service_payments = sum(float(payment.get('amount') or 0.0) for payment in booking_services_as_payments)
    total_payments_amount = total_real_payments + total_service_payments
    remainder = total_plan - (total_fact + total_payments_amount)
    
    return templates.TemplateResponse("payments.html", {
        "request": request,
        "payments": combined_payments,
        "bookings_for_fact": grouped_fact_bookings,
        "bookings_with_services": bookings_with_services,
        "unique_apartments": unique_apartments,
        "filter_date": filter_date,
        "filter_date_from": filter_date_from,
        "filter_date_to": filter_date_to,
        "apartment_title": apartment_title,
        "total_plan": total_plan,
        "total_fact": total_fact,
        "total_fact_prepayment": total_fact_prepayment,
        "total_fact_payment": total_fact_payment,
        "total_payments_amount": total_payments_amount,
        "remainder": remainder,
        "active_plan": active_plan,
        "user_type": user_type
    })

@router.post("/payments/create")
async def create_payment(
    request: Request,
    db: Session = Depends(get_db),
    booking_id: Optional[str] = Form(None),
    booking_service_id: Optional[str] = Form(None),
    apartment_title: Optional[str] = Form(None),
    receipt_date: str = Form(...),
    receipt_time: Optional[str] = Form(None),
    amount: str = Form(...),
    operation_type: Optional[str] = Form(None),
    income_category: Optional[str] = Form(None),
    comment: Optional[str] = Form(None)
):
    """
    Создать новое поступление
    """
    # Логирование входящих данных
    logger.info("=== Создание поступления (функция успешно вызвана) ===")
    logger.info(f"booking_id: {booking_id} (type: {type(booking_id)})")
    logger.info(f"booking_service_id: {booking_service_id} (type: {type(booking_service_id)})")
    logger.info(f"apartment_title: '{apartment_title}' (type: {type(apartment_title)})")
    logger.info(f"receipt_date: '{receipt_date}' (type: {type(receipt_date)})")
    logger.info(f"receipt_time: '{receipt_time}' (type: {type(receipt_time)})")
    logger.info(f"amount: {amount} (type: {type(amount)})")
    logger.info(f"operation_type: '{operation_type}' (type: {type(operation_type)})")
    logger.info(f"income_category: '{income_category}' (type: {type(income_category)})")
    logger.info(f"comment: '{comment}' (type: {type(comment)})")
    
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
        # Преобразование строк в нужные типы, обработка пустых строк
        booking_id_int = None
        if booking_id and booking_id.strip():
            try:
                booking_id_int = int(booking_id)
            except ValueError:
                logger.warning(f"Некорректный booking_id: '{booking_id}'")
        
        booking_service_id_int = None
        if booking_service_id and booking_service_id.strip():
            try:
                booking_service_id_int = int(booking_service_id)
            except ValueError:
                logger.warning(f"Некорректный booking_service_id: '{booking_service_id}'")
        
        amount_float = float(amount)
        
        # Если указано бронирование, получаем apartment_title из него
        if booking_id_int and not apartment_title:
            logger.info(f"Получаем apartment_title из бронирования ID: {booking_id_int}")
            booking = crud.get_booking_by_id(db, booking_id_int)
            if booking:
                apartment_title = booking.apartment_title
                logger.info(f"Получен apartment_title: '{apartment_title}'")
            else:
                logger.warning(f"Бронирование с ID {booking_id_int} не найдено")
        
        # Проверка обязательного поля
        if not apartment_title:
            logger.error("apartment_title отсутствует после всех проверок")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Не указан объект недвижимости"}
            )
        
        # Парсинг даты и времени
        receipt_date_obj = date.fromisoformat(receipt_date)
        receipt_time_obj = None
        if receipt_time and receipt_time.strip():
            try:
                hour, minute = map(int, receipt_time.split(':'))
                receipt_time_obj = time(hour=hour, minute=minute)
                logger.info(f"Время поступления распарсено: {receipt_time_obj}")
            except Exception as e:
                logger.warning(f"Ошибка парсинга времени '{receipt_time}': {e}")
        
        # Создание поступления
        logger.info("Создание объекта PaymentCreate...")
        logger.info(f"  - booking_id: {booking_id_int}")
        logger.info(f"  - booking_service_id: {booking_service_id_int}")
        logger.info(f"  - apartment_title: '{apartment_title}'")
        logger.info(f"  - receipt_date: {receipt_date_obj}")
        logger.info(f"  - receipt_time: {receipt_time_obj}")
        logger.info(f"  - amount: {amount_float}")
        
        payment_data = PaymentCreate(
            booking_id=booking_id_int,
            booking_service_id=booking_service_id_int,
            apartment_title=apartment_title,
            receipt_date=receipt_date_obj,
            receipt_time=receipt_time_obj,
            amount=amount_float,
            operation_type=operation_type if operation_type and operation_type.strip() else None,
            income_category=income_category if income_category and income_category.strip() else None,
            comment=comment if comment and comment.strip() else None
        )
        logger.info("PaymentCreate успешно создан")
        
        logger.info("Вызов crud.create_payment...")
        payment = crud.create_payment(db, payment_data)
        logger.info(f"Поступление успешно создано с ID: {payment.id}")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Поступление создано",
            "id": payment.id
        })
    
    except Exception as e:
        import traceback
        logger.error("=" * 50)
        logger.error("ОШИБКА при создании поступления:")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Сообщение: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 50)
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.get("/payments/list")
async def list_payments(
    request: Request,
    filter_date: Optional[str] = None,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    apartment_title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получить список поступлений в JSON формате
    Поддерживает фильтрацию по одной дате или по диапазону
    """
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
    
    # Парсинг дат фильтра
    filter_date_obj = None
    filter_date_from_obj = None
    filter_date_to_obj = None
    
    if filter_date:
        try:
            filter_date_obj = date.fromisoformat(filter_date)
        except ValueError:
            pass
    
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
    
    payments = crud.get_payments(
        db, 
        filter_date=filter_date_obj,
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj,
        apartment_title=apartment_title
    )
    
    result = []
    for payment in payments:
        result.append({
            "id": payment.id,
            "apartment_title": payment.apartment_title,
            "receipt_date": payment.receipt_date.isoformat(),
            "receipt_time": payment.receipt_time.isoformat() if payment.receipt_time else None,
            "amount": float(payment.amount),
            "operation_type": payment.operation_type,
            "income_category": payment.income_category,
            "comment": payment.comment
        })
    
    return JSONResponse(content={"payments": result})

@router.put("/payments/{payment_id}")
async def update_payment_endpoint(
    request: Request,
    payment_id: int,
    apartment_title: Optional[str] = Form(None),
    receipt_date: Optional[str] = Form(None),
    receipt_time: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),
    operation_type: Optional[str] = Form(None),
    income_category: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Обновить поступление
    """
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
        # Подготовка данных для обновления
        update_data = {}
        
        if apartment_title is not None:
            update_data["apartment_title"] = apartment_title
        
        if receipt_date is not None:
            update_data["receipt_date"] = date.fromisoformat(receipt_date)
        
        if receipt_time is not None:
            try:
                hour, minute = map(int, receipt_time.split(':'))
                update_data["receipt_time"] = time(hour=hour, minute=minute)
            except:
                pass
        
        if amount is not None:
            update_data["amount"] = amount
        
        if operation_type is not None:
            update_data["operation_type"] = operation_type
        
        if income_category is not None:
            update_data["income_category"] = income_category
        
        if comment is not None:
            update_data["comment"] = comment
        
        payment_update = PaymentUpdate(**update_data)
        payment = crud.update_payment(db, payment_id, payment_update)
        
        if not payment:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Поступление не найдено"}
            )
        
        return JSONResponse(content={
            "status": "success",
            "message": "Поступление обновлено"
        })
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении поступления: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@router.delete("/payments/{payment_id}")
async def delete_payment_endpoint(
    request: Request,
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    Удалить поступление
    """
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
    
    success = crud.delete_payment(db, payment_id)
    
    if not success:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Поступление не найдено"}
        )
    
    return JSONResponse(content={
        "status": "success",
        "message": "Поступление удалено"
    })
