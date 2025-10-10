from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, time
from loguru import logger

from app.database import get_db
from app.schemas import PaymentCreate, PaymentUpdate, PaymentResponse
from app.config import get_settings
from app import crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def check_auth(request: Request) -> bool:
    """Проверка авторизации через session cookie"""
    session_token = request.cookies.get("session_token")
    return session_token == settings.secret_key


@router.get("/payments", response_class=HTMLResponse)
async def payments_page(
    request: Request,
    filter_date: Optional[str] = None,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Страница с таблицей поступлений денег
    """
    if not check_auth(request):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Пожалуйста, войдите в систему"
        })
    
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
    
    # Получаем поступления из таблицы payments
    payments_list = crud.get_payments(
        db, 
        filter_date=filter_date_obj,
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj
    )
    
    # Получаем услуги из booking_services как поступления
    booking_services_as_payments = crud.get_booking_services_as_payments(
        db,
        filter_date=filter_date_obj,
        filter_date_from=filter_date_from_obj,
        filter_date_to=filter_date_to_obj
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
            'advance_for_future': float(p.advance_for_future) if p.advance_for_future else None,
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
    
    # Расчет плана и факта (только по реальным поступлениям)
    total_plan = sum(float(p['advance_for_future']) if p['advance_for_future'] else 0.0 for p in combined_payments if not p['is_from_booking_service'])
    total_fact = sum(float(p['amount']) for p in combined_payments if not p['is_from_booking_service'])
    total_advance = total_fact - total_plan
    
    return templates.TemplateResponse("payments.html", {
        "request": request,
        "payments": combined_payments,
        "bookings_with_services": bookings_with_services,
        "unique_apartments": unique_apartments,
        "filter_date": filter_date,
        "filter_date_from": filter_date_from,
        "filter_date_to": filter_date_to,
        "total_plan": total_plan,
        "total_fact": total_fact,
        "total_advance": total_advance
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
    advance_for_future: Optional[str] = Form(None),
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
    logger.info(f"advance_for_future: {advance_for_future} (type: {type(advance_for_future)})")
    logger.info(f"operation_type: '{operation_type}' (type: {type(operation_type)})")
    logger.info(f"income_category: '{income_category}' (type: {type(income_category)})")
    logger.info(f"comment: '{comment}' (type: {type(comment)})")
    
    if not check_auth(request):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
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
        
        advance_for_future_float = None
        if advance_for_future and advance_for_future.strip():
            try:
                advance_for_future_float = float(advance_for_future)
            except ValueError:
                logger.warning(f"Некорректный advance_for_future: '{advance_for_future}'")
        
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
        logger.info(f"  - advance_for_future: {advance_for_future_float}")
        
        payment_data = PaymentCreate(
            booking_id=booking_id_int,
            booking_service_id=booking_service_id_int,
            apartment_title=apartment_title,
            receipt_date=receipt_date_obj,
            receipt_time=receipt_time_obj,
            amount=amount_float,
            advance_for_future=advance_for_future_float,
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
    if not check_auth(request):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
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
            "advance_for_future": float(payment.advance_for_future) if payment.advance_for_future else None,
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
    advance_for_future: Optional[float] = Form(None),
    operation_type: Optional[str] = Form(None),
    income_category: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Обновить поступление
    """
    if not check_auth(request):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
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
        
        if advance_for_future is not None:
            update_data["advance_for_future"] = advance_for_future
        
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
    if not check_auth(request):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
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


@router.get("/payments/calculate-advance")
async def calculate_advance(
    request: Request,
    apartment_title: str,
    selected_date: str,
    db: Session = Depends(get_db)
):
    """
    Рассчитать сумму авансов на будущие заселения
    """
    if not check_auth(request):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Не авторизован"}
        )
    
    try:
        selected_date_obj = date.fromisoformat(selected_date)
        total_advance = crud.calculate_advance_for_future_bookings(
            db, apartment_title, selected_date_obj
        )
        
        return JSONResponse(content={
            "status": "success",
            "total_advance": total_advance
        })
    
    except Exception as e:
        logger.error(f"Ошибка при расчете аванса: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

