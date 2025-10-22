from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models import Booking, Service, BookingService, Payment
from app.schemas import BookingSchema, PaymentCreate, PaymentUpdate
from datetime import date, datetime
from typing import Optional, List
from loguru import logger


def create_or_update_booking(db: Session, booking_data: BookingSchema, action: str, status: str) -> Booking:
    """
    Создает новое бронирование или обновляет существующее
    """
    # Проверяем, существует ли уже бронирование с таким ID
    existing_booking = db.query(Booking).filter(Booking.id == booking_data.id).first()
    
    # Извлекаем данные из apartment если они есть
    apartment_title = None
    apartment_address = None
    if booking_data.apartment:
        apartment_title = booking_data.apartment.title
        apartment_address = booking_data.apartment.address
    
    # Если нет apartment объекта, используем address напрямую
    if not apartment_address and booking_data.address:
        apartment_address = booking_data.address
    
    # Извлекаем данные клиента если они есть
    client_fio = None
    client_phone = None
    client_email = None
    if booking_data.client:
        client_fio = booking_data.client.fio
        client_phone = booking_data.client.phone
        client_email = booking_data.client.email
    
    booking_dict = {
        "action": action,
        "status": status,
        "begin_date": booking_data.begin_date,
        "end_date": booking_data.end_date,
        "realty_id": booking_data.realty_id,
        "client_id": booking_data.client_id,
        "amount": booking_data.amount,
        "prepayment": booking_data.prepayment,
        "payment": booking_data.payment,
        "arrival_time": booking_data.arrival_time,
        "departure_time": booking_data.departure_time,
        "notes": booking_data.notes,
        "client_fio": client_fio,
        "client_phone": client_phone,
        "client_email": client_email,
        "apartment_title": apartment_title,
        "apartment_address": apartment_address,
        "number_of_days": booking_data.number_of_days,
        "number_of_nights": booking_data.number_of_nights,
        "is_delete": booking_data.is_delete,
        "webhook_created_at": booking_data.created_at,
        "webhook_updated_at": booking_data.updated_at,
    }
    
    if existing_booking:
        # Обновляем существующее бронирование
        for key, value in booking_dict.items():
            setattr(existing_booking, key, value)
        existing_booking.updated_at = datetime.utcnow()
        logger.info(f"Обновлено бронирование ID: {booking_data.id}")
        db.commit()
        db.refresh(existing_booking)
        return existing_booking
    else:
        # Создаем новое бронирование
        booking_dict["id"] = booking_data.id
        new_booking = Booking(**booking_dict)
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        logger.info(f"Создано новое бронирование ID: {booking_data.id}")
        return new_booking


def mark_booking_as_deleted(db: Session, booking_data: BookingSchema, action: str, status: str) -> Booking:
    """
    Помечает бронирование как удаленное
    """
    booking = create_or_update_booking(db, booking_data, action, status)
    booking.is_delete = True
    booking.status = "deleted"
    db.commit()
    db.refresh(booking)
    logger.info(f"Бронирование ID {booking_data.id} помечено как удаленное")
    return booking


def get_bookings(
    db: Session,
    filter_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 1000
) -> List[Booking]:
    """
    Получить список бронирований с опциональной фильтрацией по дате
    Фильтр выбирает бронирования где выбранная дата является датой заселения ИЛИ выселения
    Возвращаем только не удаленные бронирования
    """
    query = db.query(Booking).filter(Booking.is_delete == False)
    
    if filter_date:
        # Выбираем записи где begin_date или end_date совпадают с filter_date
        query = query.filter(
            or_(
                Booking.begin_date == filter_date,
                Booking.end_date == filter_date
            )
        )
    
    # Сортировка по дате заезда
    query = query.order_by(Booking.begin_date.desc(), Booking.id.desc())
    
    return query.offset(skip).limit(limit).all()


def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    """
    Получить бронирование по ID
    """
    return db.query(Booking).filter(Booking.id == booking_id).first()


def get_grouped_bookings(
    db: Session,
    filter_date: Optional[date] = None
) -> List[dict]:
    """
    Получить сгруппированные бронирования для отображения
    Группирует по адресу и дате если есть выселение и заселение на один адрес
    Группирует дубли (например "00) 29" и "00) 29 ДУБЛЬ") вместе, размещает их рядом
    Помечает группы дублей флагами для применения жирных границ (сверху и снизу группы)
    Между строками дублей внутри группы остаются обычные границы
    """
    bookings = get_bookings(db, filter_date)
    
    # Вспомогательная функция для определения базового адреса
    def get_base_address(address: str) -> str:
        """Получить базовый адрес без суффикса ДУБЛЬ (регистронезависимо)"""
        if not address:
            return ''
        
        address_clean = address.strip()
        address_upper = address_clean.upper()
        
        # Список суффиксов для удаления (в верхнем регистре)
        suffixes = ['ДУБЛЬ', 'ДУБЛ', 'ДУБЛЕ', 'ДУБ', 'DUBL', 'DOUBLE']
        
        for suffix in suffixes:
            # Проверяем с пробелом перед суффиксом
            suffix_with_space = ' ' + suffix
            if suffix_with_space in address_upper:
                idx = address_upper.find(suffix_with_space)
                result = address_clean[:idx].strip()
                logger.debug(f"Found suffix '{suffix}' in '{address}', base: '{result}'")
                return result
            # Проверяем суффикс в конце без пробела
            elif address_upper.endswith(suffix):
                result = address_clean[:-len(suffix)].strip()
                logger.debug(f"Found suffix '{suffix}' at end of '{address}', base: '{result}'")
                return result
        
        return address_clean
    
    # Группируем по адресу и дате (каждый apartment_title отдельно)
    grouped = {}
    result = []
    
    for booking in bookings:
        # Пропускаем бронирования без указания объекта
        if not booking.apartment_title:
            continue
            
        # Определяем тип статуса на основе совпадения дат
        # Проверяем, совпадает ли дата отчета (filter_date) с датами бронирования
        is_checkout = False
        is_checkin = False
        
        if filter_date:
            # Если filter_date совпадает с end_date - это выселение
            is_checkout = (booking.end_date == filter_date)
            # Если filter_date совпадает с begin_date - это заселение
            is_checkin = (booking.begin_date == filter_date)
            
            # Ключ группировки - по адресу и дате фильтра
            key = (booking.apartment_title, filter_date)
        else:
            # Если фильтр не задан, используем begin_date как заселение
            is_checkin = True
            # Ключ группировки - по адресу и begin_date
            key = (booking.apartment_title, booking.begin_date)
        
        # Пропускаем бронирования, которые не относятся к выбранной дате
        if not is_checkout and not is_checkin:
            continue
        
        if key not in grouped:
            grouped[key] = {
                'address': booking.apartment_title,
                'date': filter_date if filter_date else booking.begin_date,
                'checkout': None,  # данные выселения
                'checkin': None,   # данные заселения
            }
        
        # Назначаем бронирование в соответствующие секции
        if is_checkout:
            grouped[key]['checkout'] = booking
        
        if is_checkin:
            grouped[key]['checkin'] = booking
    
    # Преобразуем в список
    for key, data in grouped.items():
        result.append(data)
    
    # Сортируем: сначала по адресу (алфавитный порядок, дубли после базового), затем по дате (новые первыми)
    # Используем стабильную сортировку: сначала по дате, затем по адресу
    result.sort(key=lambda x: x['date'], reverse=True)  # по дате (новые первыми)
    result.sort(key=lambda x: (get_base_address(x['address'] or '').upper(), (x['address'] or '').upper()))  # по адресу (A-Z)
    
    # Группируем по базовому адресу (без учета даты) для определения дублей
    # Дубли должны быть рядом даже если у них разные даты заселения
    duplicate_groups = {}
    for item in result:
        base_addr = get_base_address(item['address'] or '')
        group_key = base_addr  # Группируем только по базовому адресу
        
        if group_key not in duplicate_groups:
            duplicate_groups[group_key] = []
            logger.debug(f"Creating new group for base='{base_addr}'")
        
        duplicate_groups[group_key].append(item)
        logger.debug(f"Adding '{item['address'] or ''}' (date={item['date']}) to group '{base_addr}', group size now: {len(duplicate_groups[group_key])}")
    
    # Помечаем каждую строку флагами для границ
    for item in result:
        base_addr = get_base_address(item['address'] or '')
        group_key = base_addr  # Используем только базовый адрес
        group = duplicate_groups[group_key]
        
        # Определяем позицию в группе
        item_index = group.index(item)
        group_size = len(group)
        
        # Флаги для границ
        item['is_first_in_group'] = (item_index == 0)
        item['is_last_in_group'] = (item_index == group_size - 1)
        item['is_single_row'] = (group_size == 1)
        item['has_duplicate'] = (group_size > 1)
        
        # Отладочное логирование
        logger.debug(
            f"Address: '{item['address'] or ''}', Base: '{base_addr}', "
            f"Group size: {group_size}, has_duplicate: {item['has_duplicate']}, "
            f"is_first: {item['is_first_in_group']}, is_last: {item['is_last_in_group']}"
        )
    
    return result


def update_checkin_day_comments(db: Session, booking_id: int, comments: str) -> Optional[Booking]:
    """
    Обновить комментарии по оплате и проживанию в день заселения
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.checkin_day_comments = comments
        booking.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(booking)
        logger.info(f"Обновлены комментарии для бронирования ID {booking_id}")
        return booking
    return None


# CRUD для услуг
def get_all_services(db: Session, active_only: bool = True) -> List[Service]:
    """
    Получить список всех услуг
    """
    query = db.query(Service)
    if active_only:
        query = query.filter(Service.is_active == True)
    return query.order_by(Service.name).all()


def create_service(db: Session, name: str) -> Service:
    """
    Создать новую услугу
    """
    service = Service(name=name)
    db.add(service)
    db.commit()
    db.refresh(service)
    logger.info(f"Создана новая услуга: {name}")
    return service


def get_service_by_id(db: Session, service_id: int) -> Optional[Service]:
    """
    Получить услугу по ID
    """
    return db.query(Service).filter(Service.id == service_id).first()


def update_service(db: Session, service_id: int, name: str) -> Optional[Service]:
    """
    Обновить название услуги
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return None
    
    service.name = name
    service.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(service)
    logger.info(f"Обновлена услуга ID {service_id}: {name}")
    return service


def toggle_service_status(db: Session, service_id: int) -> Optional[Service]:
    """
    Переключить статус активности услуги (активировать/деактивировать)
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return None
    
    service.is_active = not service.is_active
    service.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(service)
    status = "активирована" if service.is_active else "деактивирована"
    logger.info(f"Услуга ID {service_id} {status}")
    return service


def get_booking_services(db: Session, booking_id: int) -> List[dict]:
    """
    Получить все услуги для конкретного бронирования
    """
    booking_services = db.query(BookingService).filter(
        BookingService.booking_id == booking_id
    ).all()
    
    result = []
    for bs in booking_services:
        result.append({
            'id': bs.id,
            'booking_id': bs.booking_id,
            'service_id': bs.service_id,
            'service_name': bs.service.name,
            'price': float(bs.price),
            'created_at': bs.created_at
        })
    
    return result


def add_booking_service(db: Session, booking_id: int, service_id: int, price: float) -> BookingService:
    """
    Добавить услугу к бронированию
    """
    booking_service = BookingService(
        booking_id=booking_id,
        service_id=service_id,
        price=price
    )
    db.add(booking_service)
    db.commit()
    db.refresh(booking_service)
    logger.info(f"Добавлена услуга {service_id} к бронированию {booking_id}")
    return booking_service


def delete_booking_service(db: Session, booking_service_id: int) -> bool:
    """
    Удалить услугу из бронирования
    """
    booking_service = db.query(BookingService).filter(
        BookingService.id == booking_service_id
    ).first()
    
    if booking_service:
        db.delete(booking_service)
        db.commit()
        logger.info(f"Удалена услуга ID {booking_service_id}")
        return True
    return False


def get_booking_services_total(db: Session, booking_id: int) -> float:
    """
    Получить общую сумму услуг для бронирования
    """
    total = db.query(func.sum(BookingService.price)).filter(
        BookingService.booking_id == booking_id
    ).scalar()
    
    return float(total) if total else 0.0


# CRUD для поступлений денег
def create_payment(db: Session, payment_data: PaymentCreate) -> Payment:
    """
    Создать новое поступление
    """
    payment = Payment(**payment_data.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(f"Создано новое поступление ID: {payment.id} для объекта {payment.apartment_title}")
    return payment


def get_payments(
    db: Session,
    filter_date: Optional[date] = None,
    filter_date_from: Optional[date] = None,
    filter_date_to: Optional[date] = None,
    apartment_title: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000
) -> List[Payment]:
    """
    Получить список поступлений с фильтрацией
    Поддерживает как фильтрацию по одной дате (filter_date), 
    так и по диапазону (filter_date_from, filter_date_to)
    Загружает связанные данные booking_service и service для отображения названия услуги
    """
    from sqlalchemy.orm import joinedload
    
    query = db.query(Payment).options(
        joinedload(Payment.booking_service).joinedload(BookingService.service)
    )
    
    # Фильтрация по одной дате (для обратной совместимости)
    if filter_date:
        query = query.filter(Payment.receipt_date == filter_date)
    # Или фильтрация по диапазону дат
    elif filter_date_from or filter_date_to:
        if filter_date_from:
            query = query.filter(Payment.receipt_date >= filter_date_from)
        if filter_date_to:
            query = query.filter(Payment.receipt_date <= filter_date_to)
    
    if apartment_title:
        query = query.filter(Payment.apartment_title == apartment_title)
    
    query = query.order_by(Payment.receipt_date.desc(), Payment.created_at.desc())
    
    return query.offset(skip).limit(limit).all()


def get_payment_by_id(db: Session, payment_id: int) -> Optional[Payment]:
    """
    Получить поступление по ID
    """
    return db.query(Payment).filter(Payment.id == payment_id).first()


def update_payment(db: Session, payment_id: int, payment_data: PaymentUpdate) -> Optional[Payment]:
    """
    Обновить поступление
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        return None
    
    update_data = payment_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment, key, value)
    
    payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)
    logger.info(f"Обновлено поступление ID: {payment_id}")
    return payment


def delete_payment(db: Session, payment_id: int) -> bool:
    """
    Удалить поступление
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        return False
    
    db.delete(payment)
    db.commit()
    logger.info(f"Удалено поступление ID: {payment_id}")
    return True


def calculate_advance_for_future_bookings(db: Session, apartment_title: str, selected_date: date) -> float:
    """
    Рассчитать сумму авансов на будущие заселения
    Для заселений после выбранной даты
    считает сумму всех предоплат на будущие заселения по данному объекту после выбранной даты
    """
    future_bookings = db.query(Booking).filter(
        and_(
            Booking.apartment_title == apartment_title,
            Booking.begin_date > selected_date,
            Booking.is_delete == False
        )
    ).all()
    
    total_advance = 0.0
    for booking in future_bookings:
        if booking.prepayment:
            total_advance += float(booking.prepayment)
    
    return total_advance


def get_unique_apartments(db: Session) -> List[str]:
    """
    Получить список уникальных объектов недвижимости
    Оптимизированный запрос с DISTINCT вместо загрузки всех записей
    """
    result = db.query(Booking.apartment_title).filter(
        and_(
            Booking.is_delete == False,
            Booking.apartment_title.isnot(None)
        )
    ).distinct().order_by(Booking.apartment_title).all()
    
    return [r[0] for r in result]


def get_bookings_with_services(db: Session, filter_date: Optional[date] = None) -> List[dict]:
    """
    Получить бронирования с их услугами для отображения в таблице поступлений
    Оптимизировано с использованием joinedload для избежания N+1 проблемы
    """
    from sqlalchemy.orm import joinedload
    
    query = db.query(Booking).options(
        joinedload(Booking.services).joinedload(BookingService.service)
    ).filter(Booking.is_delete == False)
    
    if filter_date:
        # Получаем бронирования где дата заселения совпадает или близка к filter_date
        query = query.filter(Booking.begin_date >= filter_date)
    
    query = query.order_by(Booking.begin_date.desc())
    bookings = query.limit(100).all()
    
    result = []
    for booking in bookings:
        booking_info = {
            'id': booking.id,
            'apartment_title': booking.apartment_title,
            'begin_date': booking.begin_date,
            'end_date': booking.end_date,
            'client_fio': booking.client_fio,
            'client_phone': booking.client_phone,
            'amount': float(booking.amount) if booking.amount else 0.0,
            'prepayment': float(booking.prepayment) if booking.prepayment else 0.0,
            'services': []
        }
        
        # Услуги уже загружены через joinedload
        for bs in booking.services:
            booking_info['services'].append({
                'id': bs.id,
                'service_id': bs.service_id,
                'service_name': bs.service.name,
                'price': float(bs.price)
            })
        
        result.append(booking_info)
    
    return result


def get_booking_services_as_payments(
    db: Session,
    filter_date: Optional[date] = None,
    filter_date_from: Optional[date] = None,
    filter_date_to: Optional[date] = None
) -> List[dict]:
    """
    Получить все услуги из booking_services в формате поступлений
    Фильтрация по дате заселения бронирования (begin_date), которая используется как дата поступления
    Оптимизировано: один JOIN запрос вместо двух отдельных
    """
    from sqlalchemy.orm import joinedload
    
    # Один оптимизированный запрос с JOIN вместо двух запросов
    query = db.query(BookingService).join(
        BookingService.booking
    ).join(
        BookingService.service
    ).options(
        joinedload(BookingService.service),
        joinedload(BookingService.booking)
    ).filter(Booking.is_delete == False)
    
    # Фильтрация по дате заселения бронирования (begin_date = receipt_date для услуг)
    if filter_date:
        # Фильтр по одной конкретной дате
        query = query.filter(Booking.begin_date == filter_date)
    elif filter_date_from or filter_date_to:
        # Фильтр по диапазону дат
        if filter_date_from:
            query = query.filter(Booking.begin_date >= filter_date_from)
        if filter_date_to:
            query = query.filter(Booking.begin_date <= filter_date_to)
    
    booking_services = query.all()
    
    result = []
    for bs in booking_services:
        # Создаем объект-заглушку для booking_service с вложенным service
        # Это нужно для совместимости с шаблоном
        class MockService:
            def __init__(self, name):
                self.name = name
        
        class MockBookingService:
            def __init__(self, service_name):
                self.service = MockService(service_name)
        
        result.append({
            'id': None,  # Нет ID поступления
            'booking_id': bs.booking_id,
            'booking_service_id': bs.id,
            'apartment_title': bs.booking.apartment_title,
            'receipt_date': bs.booking.begin_date,  # Используем дату заселения
            'receipt_time': None,
            'amount': float(bs.price),
            'advance_for_future': None,
            'operation_type': None,
            'income_category': bs.service.name,  # Название услуги
            'comment': None,
            'booking_service': MockBookingService(bs.service.name),  # Для совместимости с шаблоном
            'is_from_booking_service': True  # Флаг что это услуга из booking_services
        })
    
    return result

