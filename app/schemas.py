from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
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
    platform_tax: Optional[float] = None  # Комиссия площадки (может быть null, числом или строкой "4554.0")
    balance_to_be_paid_1: Optional[float] = None  # Доплата (может быть null или числом 16951)
    arrival_time: Optional[time] = None
    
    @field_validator('platform_tax', mode='before')
    @classmethod
    def parse_platform_tax(cls, v):
        """Преобразует platform_tax из строки в число или возвращает None
        
        Обрабатывает случаи:
        - null -> None
        - "4554.0" -> 4554.0
        - 4554.0 -> 4554.0
        """
        if v is None or v == "null" or v == "":
            return None
        if isinstance(v, str):
            v = v.strip()
            if not v or v.lower() == "null":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        if isinstance(v, (int, float)):
            return float(v)
        return None
    
    @field_validator('balance_to_be_paid_1', mode='before')
    @classmethod
    def parse_balance_to_be_paid_1(cls, v):
        """Преобразует balance_to_be_paid_1 в float или возвращает None
        
        Обрабатывает случаи:
        - null -> None
        - 16951 (int) -> 16951.0
        - 16951.0 (float) -> 16951.0
        Также обрабатывает строки на случай изменения формата
        """
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if not v or v.lower() == "null":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        if isinstance(v, (int, float)):
            return float(v)
        return None
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


# Схемы для месячных планов
class MonthlyPlanCreate(BaseModel):
    """Схема для создания месячного плана"""
    start_date: date
    end_date: date
    target_amount: float


class MonthlyPlanUpdate(BaseModel):
    """Схема для обновления месячного плана"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    target_amount: Optional[float] = None


class MonthlyPlanResponse(BaseModel):
    """Схема для ответа с месячным планом"""
    id: int
    start_date: date
    end_date: date
    target_amount: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Схемы для расходов
class ExpenseCreate(BaseModel):
    """Схема для создания расхода"""
    apartment_title: Optional[str] = None
    expense_date: date
    amount: float
    category: Optional[str] = None
    comment: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """Схема для обновления расхода"""
    apartment_title: Optional[str] = None
    expense_date: Optional[date] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    comment: Optional[str] = None


class ExpenseResponse(BaseModel):
    """Схема для ответа с расходом"""
    id: int
    apartment_title: Optional[str] = None
    expense_date: date
    amount: float
    category: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Схемы для объектов недвижимости
class RealtyCreate(BaseModel):
    """Схема для создания объекта недвижимости"""
    name: str
    is_active: Optional[bool] = True


class RealtyUpdate(BaseModel):
    """Схема для обновления объекта недвижимости"""
    name: Optional[str] = None
    is_active: Optional[bool] = None


class RealtyResponse(BaseModel):
    """Схема для ответа с объектом недвижимости"""
    id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
