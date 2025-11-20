from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, Time, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Booking(Base):
    """Модель бронирования недвижимости"""
    __tablename__ = "bookings"

    # Основные поля
    id = Column(Integer, primary_key=True, index=True)  # ID из booking.id
    action = Column(String, nullable=False)  # create_booking, update_booking, delete_booking
    status = Column(String, nullable=False)  # booked, deleted
    
    # Даты бронирования
    begin_date = Column(Date, nullable=False, index=True)  # Дата заезда
    end_date = Column(Date, nullable=False)  # Дата выезда
    
    # ID связанных объектов
    realty_id = Column(Integer, nullable=False)
    client_id = Column(Integer, nullable=True)  # Может быть None при удалении бронирования
    
    # Финансовые данные
    amount = Column(Numeric(10, 2), nullable=True)  # Общая сумма
    prepayment = Column(Numeric(10, 2), nullable=True)  # Предоплата
    payment = Column(Numeric(10, 2), nullable=True)  # Оплата
    
    # Время заезда/выезда
    arrival_time = Column(Time, nullable=True)  # Время заселения
    departure_time = Column(Time, nullable=True)  # Время выселения
    
    # Комментарии
    notes = Column(String, nullable=True)
    checkin_day_comments = Column(String, nullable=True)  # Комментарии по оплате и проживанию в день заселения
    
    # Данные клиента
    client_fio = Column(String, nullable=True)
    client_phone = Column(String, nullable=True)
    client_email = Column(String, nullable=True)
    
    # Данные квартиры
    apartment_title = Column(String, nullable=True, index=True)
    apartment_address = Column(String, nullable=True)
    
    # Дополнительная информация
    number_of_days = Column(Integer, nullable=True)
    number_of_nights = Column(Integer, nullable=True)
    
    # Флаги и временные метки
    is_delete = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Временные метки из webhook
    webhook_created_at = Column(DateTime, nullable=True)
    webhook_updated_at = Column(DateTime, nullable=True)
    
    # Связь с услугами
    services = relationship("BookingService", back_populates="booking", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Booking(id={self.id}, client_fio={self.client_fio}, begin_date={self.begin_date})>"


class Service(Base):
    """Справочник дополнительных услуг"""
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Название услуги
    is_active = Column(Boolean, default=True)  # Активна ли услуга
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с бронированиями
    booking_services = relationship("BookingService", back_populates="service")
    
    def __repr__(self):
        return f"<Service(id={self.id}, name={self.name})>"


class BookingService(Base):
    """Дополнительные услуги к бронированию"""
    __tablename__ = "booking_services"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)  # Цена услуги
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    booking = relationship("Booking", back_populates="services")
    service = relationship("Service", back_populates="booking_services")
    
    def __repr__(self):
        return f"<BookingService(id={self.id}, booking_id={self.booking_id}, service_id={self.service_id}, price={self.price})>"


class Payment(Base):
    """Модель поступлений денег"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True)  # Связь с бронированием
    booking_service_id = Column(Integer, ForeignKey("booking_services.id", ondelete="SET NULL"), nullable=True, index=True)  # Связь с услугой бронирования
    apartment_title = Column(String, nullable=True)  # Объект (может браться из booking)
    realty_id = Column(Integer, nullable=True)  # ID недвижимости (опционально)
    receipt_date = Column(Date, nullable=False, index=True)  # Дата поступления
    receipt_time = Column(Time, nullable=True)  # Время поступления
    amount = Column(Numeric(10, 2), nullable=False)  # Сумма поступления
    advance_for_future = Column(Numeric(10, 2), nullable=True)  # Сумма аванса на будущее заселение
    operation_type = Column(String, nullable=True)  # Тип операции
    income_category = Column(String, nullable=True)  # Статья поступления (название услуги или другая категория)
    comment = Column(String, nullable=True)  # Комментарий
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    booking = relationship("Booking", foreign_keys=[booking_id])
    booking_service = relationship("BookingService", foreign_keys=[booking_service_id])
    
    def __repr__(self):
        return f"<Payment(id={self.id}, apartment_title={self.apartment_title}, receipt_date={self.receipt_date}, amount={self.amount})>"


class MonthlyPlan(Base):
    """Модель месячных планов поступлений"""
    __tablename__ = "monthly_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    target_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MonthlyPlan(id={self.id}, start_date={self.start_date}, end_date={self.end_date}, target_amount={self.target_amount})>"


class Expense(Base):
    """Модель расходов"""
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    apartment_title = Column(String, nullable=True)  # Объект (опционально)
    expense_date = Column(Date, nullable=False, index=True)  # Дата расхода
    amount = Column(Numeric(10, 2), nullable=False)  # Сумма расхода
    category = Column(String, nullable=True)  # Категория расхода
    comment = Column(String, nullable=True)  # Комментарий
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Expense(id={self.id}, apartment_title={self.apartment_title}, expense_date={self.expense_date}, amount={self.amount})>"
