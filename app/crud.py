from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models import Booking, Service, BookingService, Payment, MonthlyPlan, Expense, Realty
from app.schemas import BookingSchema, PaymentCreate, PaymentUpdate, MonthlyPlanCreate, MonthlyPlanUpdate, ExpenseCreate, ExpenseUpdate, RealtyCreate, RealtyUpdate
from datetime import date, datetime
from typing import Optional, List
import re
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
        "platform_tax": booking_data.platform_tax,
        "balance_to_be_paid_1": booking_data.balance_to_be_paid_1,
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
    
    # Фильтрация по активным объектам
    # Получаем список неактивных объектов
    inactive_realty = db.query(Realty.name).filter(Realty.is_active == False).all()
    inactive_names = [r[0] for r in inactive_realty]
    
    if inactive_names:
        query = query.filter(Booking.apartment_title.notin_(inactive_names))
    
    # Сортировка по дате заезда
    query = query.order_by(Booking.begin_date.desc(), Booking.id.desc())
    
    return query.offset(skip).limit(limit).all()


def get_bookings_by_begin_date(
    db: Session,
    filter_date: Optional[date] = None,
    filter_date_from: Optional[date] = None,
    filter_date_to: Optional[date] = None,
    apartment_title: Optional[str] = None
) -> List[Booking]:
    """
    Получить бронирования по begin_date (используется для расчета факта заселений)
    При указании apartment_title учитываем сам объект и его дубли (название с суффиксом ДУБЛЬ)
    """
    query = db.query(Booking).filter(Booking.is_delete == False)

    if filter_date:
        query = query.filter(Booking.begin_date == filter_date)
    elif filter_date_from or filter_date_to:
        if filter_date_from:
            query = query.filter(Booking.begin_date >= filter_date_from)
        if filter_date_to:
            query = query.filter(Booking.begin_date <= filter_date_to)

    if apartment_title:
        base_title = apartment_title.strip()
        if base_title:
            # Удаляем ведущие числа для поиска
            base_title_clean = re.sub(r'^\d+(?:\.\d+)?\)\s*', '', base_title)
            base_upper = base_title_clean.upper()
            duplicate_pattern = f"{base_upper} %ДУБ%"
            query = query.filter(
                or_(
                    func.upper(Booking.apartment_title).like(f"%{base_upper}"),
                    func.upper(Booking.apartment_title).like(duplicate_pattern)
                )
            )

    # Фильтрация по активным объектам
    inactive_realty = db.query(Realty.name).filter(Realty.is_active == False).all()
    inactive_names = [r[0] for r in inactive_realty]
    
    if inactive_names:
        query = query.filter(Booking.apartment_title.notin_(inactive_names))

    query = query.order_by(Booking.begin_date.desc())
    return query.all()


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
        """Получить базовый адрес без суффикса ДУБЛЬ (регистронезависимо) и без ведущих чисел"""
        if not address:
            return ''
        
        address_clean = address.strip()
        
        # Удаляем ведущие числа в формате '123) ' или '123.4) '
        # Например: "004) 29Б" -> "29Б" или "011.2) Ш15" -> "Ш15"
        address_clean = re.sub(r'^\d+(?:\.\d+)?\)\s*', '', address_clean)
        
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
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise ValueError(f"Бронирование ID {booking_id} не найдено")
    
    service_created_at = datetime.combine(booking.begin_date, datetime.min.time()) if booking.begin_date else datetime.utcnow()
    
    booking_service = BookingService(
        booking_id=booking_id,
        service_id=service_id,
        price=price,
        created_at=service_created_at
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
    
    # Автоматически добавляем объект в Realty, если его там нет
    if payment.apartment_title:
        exists = db.query(Realty).filter(Realty.name == payment.apartment_title).first()
        if not exists:
            try:
                new_realty = Realty(name=payment.apartment_title, is_active=True)
                db.add(new_realty)
                db.commit()
                logger.info(f"Auto-added realty object '{payment.apartment_title}' from payment")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to auto-create realty '{payment.apartment_title}': {e}")
    
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


def sync_realty_from_all_sources(db: Session):
    """
    Синхронизирует таблицу Realty со всеми источниками данных:
    - bookings (apartment_title)
    - payments (apartment_title)
    - expenses (apartment_title)
    Добавляет новые объекты, если их еще нет в Realty.
    """
    all_titles = set()
    
    # Собираем объекты из bookings
    bookings_titles = db.query(Booking.apartment_title).filter(
        and_(
            Booking.is_delete == False,
            Booking.apartment_title.isnot(None)
        )
    ).distinct().all()
    for title in bookings_titles:
        if title[0]:
            all_titles.add(title[0])
    
    # Собираем объекты из payments
    payments_titles = db.query(Payment.apartment_title).filter(
        Payment.apartment_title.isnot(None)
    ).distinct().all()
    for title in payments_titles:
        if title[0]:
            all_titles.add(title[0])
    
    # Собираем объекты из expenses
    expenses_titles = db.query(Expense.apartment_title).filter(
        Expense.apartment_title.isnot(None)
    ).distinct().all()
    for title in expenses_titles:
        if title[0]:
            all_titles.add(title[0])
    
    # Добавляем отсутствующие объекты в Realty
    added_count = 0
    for title in all_titles:
        exists = db.query(Realty).filter(Realty.name == title).first()
        if not exists:
            try:
                new_realty = Realty(name=title, is_active=True)
                db.add(new_realty)
                added_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create realty '{title}': {e}")
    
    if added_count > 0:
        db.commit()
        logger.info(f"Added {added_count} new realty objects from all sources")


def get_unique_apartments(db: Session) -> List[str]:
    """
    Получить список уникальных объектов недвижимости.
    Если таблица Realty не пуста, берет активные объекты оттуда.
    Если пуста, синхронизирует из всех источников (bookings, payments, expenses) и заполняет Realty.
    """
    # Проверяем, есть ли записи в Realty
    realty_count = db.query(Realty).count()
    
    if realty_count > 0:
        # Если есть, возвращаем только активные
        result = db.query(Realty.name).filter(Realty.is_active == True).order_by(Realty.name).all()
        return [r[0] for r in result]
    else:
        # Если нет, синхронизируем из всех источников
        sync_realty_from_all_sources(db)
        
        # Теперь возвращаем активные объекты из Realty
        result = db.query(Realty.name).filter(Realty.is_active == True).order_by(Realty.name).all()
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
    filter_date_to: Optional[date] = None,
    apartment_title: Optional[str] = None
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

    if apartment_title:
        query = query.filter(Booking.apartment_title == apartment_title)
    
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


# CRUD для месячных планов
def create_monthly_plan(db: Session, plan_data: MonthlyPlanCreate) -> MonthlyPlan:
    """
    Создать новый месячный план
    """
    plan = MonthlyPlan(**plan_data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    logger.info(f"Создан новый план ID: {plan.id} на период {plan.start_date} - {plan.end_date}")
    return plan


def get_all_plans(db: Session) -> List[MonthlyPlan]:
    """
    Получить список всех планов
    """
    return db.query(MonthlyPlan).order_by(MonthlyPlan.start_date.desc()).all()


def get_active_plan_for_period(db: Session, start_date: date, end_date: date) -> Optional[MonthlyPlan]:
    """
    Найти активный план для заданного периода (пересечение дат)
    """
    plan = db.query(MonthlyPlan).filter(
        and_(
            MonthlyPlan.start_date <= end_date,
            MonthlyPlan.end_date >= start_date
        )
    ).first()
    return plan


def update_monthly_plan(db: Session, plan_id: int, plan_data: MonthlyPlanUpdate) -> Optional[MonthlyPlan]:
    """
    Обновить месячный план
    """
    plan = db.query(MonthlyPlan).filter(MonthlyPlan.id == plan_id).first()
    if not plan:
        return None
    
    update_data = plan_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)
    
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    logger.info(f"Обновлен план ID: {plan_id}")
    return plan


def delete_monthly_plan(db: Session, plan_id: int) -> bool:
    """
    Удалить месячный план
    """
    plan = db.query(MonthlyPlan).filter(MonthlyPlan.id == plan_id).first()
    if not plan:
        return False
    
    db.delete(plan)
    db.commit()
    logger.info(f"Удален план ID: {plan_id}")
    return True


# CRUD для расходов
def create_expense(db: Session, expense_data: ExpenseCreate) -> Expense:
    """
    Создать новый расход
    """
    expense = Expense(**expense_data.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    
    # Автоматически добавляем объект в Realty, если его там нет
    if expense.apartment_title:
        exists = db.query(Realty).filter(Realty.name == expense.apartment_title).first()
        if not exists:
            try:
                new_realty = Realty(name=expense.apartment_title, is_active=True)
                db.add(new_realty)
                db.commit()
                logger.info(f"Auto-added realty object '{expense.apartment_title}' from expense")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to auto-create realty '{expense.apartment_title}': {e}")
    
    logger.info(f"Создан новый расход ID: {expense.id} для объекта {expense.apartment_title}")
    return expense


def get_expenses(
    db: Session,
    filter_date: Optional[date] = None,
    filter_date_from: Optional[date] = None,
    filter_date_to: Optional[date] = None,
    apartment_title: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000
) -> List[Expense]:
    """
    Получить список расходов с фильтрацией
    Поддерживает как фильтрацию по одной дате (filter_date), 
    так и по диапазону (filter_date_from, filter_date_to)
    """
    query = db.query(Expense)
    
    # Фильтрация по одной дате (для обратной совместимости)
    if filter_date:
        query = query.filter(Expense.expense_date == filter_date)
    # Или фильтрация по диапазону дат
    elif filter_date_from or filter_date_to:
        if filter_date_from:
            query = query.filter(Expense.expense_date >= filter_date_from)
        if filter_date_to:
            query = query.filter(Expense.expense_date <= filter_date_to)
    
    if apartment_title:
        query = query.filter(Expense.apartment_title == apartment_title)
    
    query = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
    
    return query.offset(skip).limit(limit).all()


    return db.query(Expense).filter(Expense.id == expense_id).first()


def update_expense(db: Session, expense_id: int, expense_data: ExpenseUpdate) -> Optional[Expense]:
    """
    Обновить расход
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return None
    
    update_data = expense_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(expense, key, value)
    
    expense.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(expense)
    logger.info(f"Обновлен расход ID: {expense_id}")
    return expense


def delete_expense(db: Session, expense_id: int) -> bool:
    """
    Удалить расход
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return False
    
    db.delete(expense)
    db.commit()
    logger.info(f"Удален расход ID: {expense_id}")
    return True


# CRUD для объектов недвижимости (Realty)
def get_all_realty(db: Session) -> List[Realty]:
    """
    Получить список всех объектов недвижимости (включая неактивные)
    """
    return db.query(Realty).order_by(Realty.name).all()


def create_realty(db: Session, realty_data: RealtyCreate) -> Realty:
    """
    Создать новый объект недвижимости
    """
    realty = Realty(**realty_data.model_dump())
    db.add(realty)
    db.commit()
    db.refresh(realty)
    logger.info(f"Создан новый объект недвижимости: {realty.name}")
    return realty


def get_realty_by_id(db: Session, realty_id: int) -> Optional[Realty]:
    """
    Получить объект недвижимости по ID
    """
    return db.query(Realty).filter(Realty.id == realty_id).first()


def update_realty(db: Session, realty_id: int, realty_data: RealtyUpdate) -> Optional[Realty]:
    """
    Обновить объект недвижимости
    """
    realty = db.query(Realty).filter(Realty.id == realty_id).first()
    if not realty:
        return None
    
    update_data = realty_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(realty, key, value)
    
    realty.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(realty)
    logger.info(f"Обновлен объект недвижимости ID {realty_id}")
    return realty


def update_bookings_apartment_title(db: Session, old_title: str, new_title: str):
    """
    Обновить название объекта во всех бронированиях
    """
    # Обновляем bookings
    db.query(Booking).filter(Booking.apartment_title == old_title).update(
        {Booking.apartment_title: new_title},
        synchronize_session=False
    )
    
    # Обновляем payments (если там есть apartment_title)
    db.query(Payment).filter(Payment.apartment_title == old_title).update(
        {Payment.apartment_title: new_title},
        synchronize_session=False
    )
    
    db.commit()
    logger.info(f"Обновлено название объекта с '{old_title}' на '{new_title}' во всех связанных записях")

def get_expense_by_id(db: Session, expense_id: int) -> Optional[Expense]:
    """
    Получить расход по ID
    """
    return db.query(Expense).filter(Expense.id == expense_id).first()


def update_expense(db: Session, expense_id: int, expense_data: ExpenseUpdate) -> Optional[Expense]:
    """
    Обновить расход
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return None
    
    update_data = expense_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(expense, key, value)
    
    expense.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(expense)
    logger.info(f"Обновлен расход ID: {expense_id}")
    return expense


def delete_expense(db: Session, expense_id: int) -> bool:
    """
    Удалить расход
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return False
    
    db.delete(expense)
    db.commit()
    logger.info(f"Удален расход ID: {expense_id}")
    return True
