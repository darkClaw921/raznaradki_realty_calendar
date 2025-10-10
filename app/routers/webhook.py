from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import WebhookRequestSchema
from app.crud import create_or_update_booking, mark_booking_as_deleted
from loguru import logger
from typing import List

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint для приема webhook данных о бронированиях
    
    Обрабатывает три типа действий:
    - create_booking: создание нового бронирования
    - update_booking: обновление существующего бронирования
    - delete_booking: удаление бронирования
    """
    try:
        # Получаем raw body для логирования
        body = await request.json()
        logger.info(f"Получен webhook: {body}")
        
        # Webhook приходит как массив объектов
        if isinstance(body, list):
            results = []
            for item in body:
                webhook_data = WebhookRequestSchema(**item)
                result = process_webhook(db, webhook_data)
                results.append(result)
            return {"status": "success", "processed": len(results), "results": results}
        else:
            # Если пришел один объект
            webhook_data = WebhookRequestSchema(**body)
            result = process_webhook(db, webhook_data)
            return {"status": "success", "result": result}
            
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Ошибка обработки данных: {str(e)}")


def process_webhook(db: Session, webhook_data: WebhookRequestSchema) -> dict:
    """
    Обработка одного webhook запроса
    """
    action = webhook_data.action
    status = webhook_data.status
    booking_data = webhook_data.data.booking
    
    logger.info(f"Обработка действия: {action} для бронирования ID: {booking_data.id}")
    
    if action == "delete_booking":
        booking = mark_booking_as_deleted(db, booking_data, action, status)
    else:
        # create_booking или update_booking
        booking = create_or_update_booking(db, booking_data, action, status)
    
    return {
        "action": action,
        "booking_id": booking.id,
        "status": booking.status
    }

