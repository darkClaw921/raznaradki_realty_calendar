from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time, datetime


# Схемы для услуг
class ServiceCreate(BaseModel):
    """Схема для создания услуги"""
    name: str


class ServiceResponse(BaseModel):
    """Схема для ответа с услугой"""
    id: int
    name: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookingServiceCreate(BaseModel):
    """Схема для добавления услуги к бронированию"""
    booking_id: int
    service_id: int
    price: float


class BookingServiceResponse(BaseModel):
    """Схема для ответа с услугой бронирования"""
    id: int
    booking_id: int
    service_id: int
    price: float
    service_name: str  # Название услуги
    created_at: datetime
    
    class Config:
        from_attributes = True


# Webhook схемы
class ClientSchema(BaseModel):
    """Схема данных клиента из webhook"""
    id: int
    fio: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    additional_phone: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Игнорируем дополнительные поля


class ApartmentSchema(BaseModel):
    """Схема данных квартиры из webhook"""
    id: int
    title: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Игнорируем дополнительные поля


class BookingSchema(BaseModel):
    """Схема данных бронирования из webhook"""
    id: int
    begin_date: date
    end_date: date
    realty_id: int
    client_id: Optional[int] = None  # Опциональное поле (может быть None при удалении)
    amount: Optional[float] = None
    prepayment: Optional[float] = None
    payment: Optional[float] = None
    arrival_time: Optional[time] = None
    departure_time: Optional[time] = None
    notes: Optional[str] = None
    client: Optional[ClientSchema] = None  # Опциональное поле (может отсутствовать при удалении)
    apartment: Optional[ApartmentSchema] = None
    address: Optional[str] = None
    number_of_days: Optional[int] = None
    number_of_nights: Optional[int] = None
    is_delete: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        extra = "ignore"  # Игнорируем дополнительные поля (payments_with_deleted, url и т.д.)


class WebhookDataSchema(BaseModel):
    """Схема данных внутри webhook body"""
    booking: BookingSchema
    
    class Config:
        extra = "ignore"  # Игнорируем дополнительные поля


class WebhookPayloadSchema(BaseModel):
    """Полная схема webhook payload - игнорируем дополнительные поля"""
    action: str
    status: str
    data: WebhookDataSchema
    
    class Config:
        extra = "ignore"  # Игнорируем дополнительные поля вроде changes, crm_entity_id и т.д.


# WebhookRequestSchema теперь алиас для WebhookPayloadSchema (данные приходят напрямую без обёртки body)
WebhookRequestSchema = WebhookPayloadSchema


# Схемы для поступлений денег
class PaymentCreate(BaseModel):
    """Схема для создания поступления"""
    booking_id: Optional[int] = None
    booking_service_id: Optional[int] = None
    apartment_title: Optional[str] = None
    realty_id: Optional[int] = None
    receipt_date: date
    receipt_time: Optional[time] = None
    amount: float
    advance_for_future: Optional[float] = None
    operation_type: Optional[str] = None
    income_category: Optional[str] = None
    comment: Optional[str] = None


class PaymentUpdate(BaseModel):
    """Схема для обновления поступления"""
    booking_id: Optional[int] = None
    booking_service_id: Optional[int] = None
    apartment_title: Optional[str] = None
    realty_id: Optional[int] = None
    receipt_date: Optional[date] = None
    receipt_time: Optional[time] = None
    amount: Optional[float] = None
    advance_for_future: Optional[float] = None
    operation_type: Optional[str] = None
    income_category: Optional[str] = None
    comment: Optional[str] = None


class PaymentResponse(BaseModel):
    """Схема для ответа с поступлением"""
    id: int
    booking_id: Optional[int] = None
    booking_service_id: Optional[int] = None
    apartment_title: Optional[str] = None
    realty_id: Optional[int] = None
    receipt_date: date
    receipt_time: Optional[time] = None
    amount: float
    advance_for_future: Optional[float] = None
    operation_type: Optional[str] = None
    income_category: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

