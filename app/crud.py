from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models import Booking, Service, BookingService
from app.schemas import BookingSchema
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
        "client_fio": booking_data.client.fio,
        "client_phone": booking_data.client.phone,
        "client_email": booking_data.client.email,
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
        # Используем полный apartment_title как ключ
        key = (booking.apartment_title, booking.begin_date)
        
        if key not in grouped:
            grouped[key] = {
                'address': booking.apartment_title,
                'date': booking.begin_date,
                'checkout': None,  # данные выселения
                'checkin': None,   # данные заселения
            }
        
        # Определяем тип статуса
        status_lower = booking.status.lower() if booking.status else ''
        
        # Если это выселение или содержит "выс"
        if 'выс' in status_lower or status_lower == 'checkout':
            grouped[key]['checkout'] = booking
        
        # Если это заселение или содержит "зас" или "booked"
        if 'зас' in status_lower or status_lower == 'checkin' or status_lower == 'booked':
            grouped[key]['checkin'] = booking
    
    # Преобразуем в список
    for key, data in grouped.items():
        result.append(data)
    
    # Сортируем по дате и адресу (базовый адрес сначала, потом дубль)
    result.sort(key=lambda x: (x['date'], get_base_address(x['address']), x['address']), reverse=True)
    
    # Группируем по базовому адресу (без учета даты) для определения дублей
    # Дубли должны быть рядом даже если у них разные даты заселения
    duplicate_groups = {}
    for item in result:
        base_addr = get_base_address(item['address'])
        group_key = base_addr  # Группируем только по базовому адресу
        
        if group_key not in duplicate_groups:
            duplicate_groups[group_key] = []
            logger.debug(f"Creating new group for base='{base_addr}'")
        
        duplicate_groups[group_key].append(item)
        logger.debug(f"Adding '{item['address']}' (date={item['date']}) to group '{base_addr}', group size now: {len(duplicate_groups[group_key])}")
    
    # Помечаем каждую строку флагами для границ
    for item in result:
        base_addr = get_base_address(item['address'])
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
            f"Address: '{item['address']}', Base: '{base_addr}', "
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
    from sqlalchemy import func
    
    total = db.query(func.sum(BookingService.price)).filter(
        BookingService.booking_id == booking_id
    ).scalar()
    
    return float(total) if total else 0.0

