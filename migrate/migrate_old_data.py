"""
Скрипт миграции данных из старой базы данных (cells.json, sheets.json) в новую БД
"""
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session

# Добавляем путь к модулям приложения
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, init_db
from app.models import Booking
from app.crud import create_or_update_booking


# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)
logger.add(
    "logs/migration.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)


def parse_date(date_str: str) -> datetime.date:
    """Парсинг даты из формата DD.MM.YYYY"""
    if not date_str or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").date()
    except ValueError:
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None


def parse_number(value: str) -> Decimal:
    """Парсинг числового значения"""
    if not value or value.strip() == "" or value == "0":
        return Decimal("0")
    try:
        # Убираем пробелы и заменяем запятую на точку
        clean_value = value.strip().replace(" ", "").replace(",", ".")
        return Decimal(clean_value)
    except Exception:
        logger.warning(f"Не удалось распарсить число: {value}")
        return Decimal("0")


def parse_int(value: str) -> int:
    """Парсинг целого числа"""
    if not value or value.strip() == "":
        return 0
    try:
        return int(value.strip())
    except ValueError:
        logger.warning(f"Не удалось распарсить целое число: {value}")
        return 0


def load_sheets_mapping(sheets_file: Path) -> dict:
    """
    Загрузка маппинга sheet_id -> apartment_title из sheets.json
    """
    logger.info(f"Загрузка маппинга листов из {sheets_file}")
    
    with open(sheets_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Находим таблицу sheets
    sheets_data = None
    for item in data:
        if item.get("type") == "table" and item.get("name") == "sheets":
            sheets_data = item.get("data", [])
            break
    
    if not sheets_data:
        logger.error("Не найдена таблица sheets в файле")
        return {}
    
    # Создаем маппинг
    mapping = {}
    for sheet in sheets_data:
        sheet_id = sheet.get("id")
        name = sheet.get("name")
        if sheet_id and name:
            mapping[sheet_id] = name
            logger.debug(f"  Sheet ID {sheet_id} -> {name}")
    
    logger.info(f"Загружено {len(mapping)} листов")
    return mapping


def load_cells_by_booking(cells_file: Path) -> dict:
    """
    Загрузка и группировка ячеек по booking_id из cells.json
    """
    logger.info(f"Загрузка ячеек из {cells_file}")
    
    with open(cells_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Находим таблицу cells
    cells_data = None
    for item in data:
        if item.get("type") == "table" and item.get("name") == "cells":
            cells_data = item.get("data", [])
            break
    
    if not cells_data:
        logger.error("Не найдена таблица cells в файле")
        return {}
    
    # Группируем по booking_id
    bookings = {}
    for cell in cells_data:
        booking_id = cell.get("booking_id")
        if not booking_id:
            continue
        
        if booking_id not in bookings:
            bookings[booking_id] = {
                "cells": {},
                "sheet_id": cell.get("sheet_id"),
                "created_at": cell.get("created_at"),
                "updated_at": cell.get("updated_at")
            }
        
        column = cell.get("column")
        value = cell.get("value", "")
        bookings[booking_id]["cells"][column] = value
    
    logger.info(f"Найдено {len(bookings)} бронирований")
    return bookings


def convert_booking_to_model(booking_id: str, booking_data: dict, sheets_mapping: dict) -> dict:
    """
    Преобразование данных из старого формата в новый
    """
    cells = booking_data["cells"]
    sheet_id = booking_data["sheet_id"]
    
    # Получаем название квартиры
    apartment_title = sheets_mapping.get(sheet_id, f"Unknown_{sheet_id}")
    
    # Парсим даты
    begin_date = parse_date(cells.get("1", ""))
    end_date = parse_date(cells.get("3", ""))
    
    # Если даты не удалось распарсить, пропускаем
    if not begin_date or not end_date:
        return None
    
    # Парсим финансовые данные
    amount = parse_number(cells.get("6", "0"))
    prepayment = parse_number(cells.get("8", "0"))
    payment = parse_number(cells.get("7", "0"))
    
    # Рассчитываем количество ночей
    number_of_days = parse_int(cells.get("2", "0"))
    number_of_nights = number_of_days if number_of_days > 0 else (end_date - begin_date).days
    
    # Собираем данные клиента
    client_fio = cells.get("4", "").strip()
    client_phone = cells.get("5", "").strip()
    
    # Комментарии
    notes = cells.get("11", "").strip()
    
    # Формируем данные для создания записи
    booking_model_data = {
        "id": int(booking_id),
        "action": "migration",
        "status": "booked",
        "begin_date": begin_date,
        "end_date": end_date,
        "apartment_title": apartment_title,
        "apartment_address": apartment_title,  # В старой БД нет отдельного адреса
        "client_fio": client_fio,
        "client_phone": client_phone,
        "client_email": "",
        "amount": amount,
        "prepayment": prepayment,
        "payment": payment,
        "number_of_days": number_of_days,
        "number_of_nights": number_of_nights,
        "notes": notes,
        "realty_id": 0,
        "client_id": 0,
        "arrival_time": None,
        "departure_time": None,
        "checkin_day_comments": "",
        "is_delete": False,
        "webhook_created_at": datetime.strptime(booking_data["created_at"], "%Y-%m-%d %H:%M:%S") if booking_data.get("created_at") else None,
        "webhook_updated_at": datetime.strptime(booking_data["updated_at"], "%Y-%m-%d %H:%M:%S") if booking_data.get("updated_at") else None,
    }
    
    return booking_model_data


def migrate_data():
    """
    Главная функция миграции
    """
    logger.info("=" * 80)
    logger.info("Начало миграции данных из старой базы")
    logger.info("=" * 80)
    
    # Пути к файлам
    base_path = Path(__file__).parent
    sheets_file = base_path / "sheets.json"
    cells_file = base_path / "cells.json"
    
    # Проверяем наличие файлов
    if not sheets_file.exists():
        logger.error(f"Файл не найден: {sheets_file}")
        return
    
    if not cells_file.exists():
        logger.error(f"Файл не найден: {cells_file}")
        return
    
    # Инициализируем БД
    logger.info("Инициализация базы данных")
    init_db()
    
    # Загружаем данные
    sheets_mapping = load_sheets_mapping(sheets_file)
    bookings_data = load_cells_by_booking(cells_file)
    
    if not sheets_mapping or not bookings_data:
        logger.error("Не удалось загрузить данные")
        return
    
    # Обрабатываем каждое бронирование
    logger.info("=" * 80)
    logger.info("Начало обработки бронирований")
    logger.info("=" * 80)
    
    success_count = 0
    error_count = 0
    skip_count = 0
    
    db: Session = SessionLocal()
    
    try:
        for booking_id, booking_data in bookings_data.items():
            try:
                # Преобразуем данные
                booking_model_data = convert_booking_to_model(booking_id, booking_data, sheets_mapping)
                
                if not booking_model_data:
                    logger.warning(f"Пропускаем бронирование {booking_id}: некорректные данные")
                    skip_count += 1
                    continue
                
                # Проверяем, существует ли уже
                existing = db.query(Booking).filter(Booking.id == int(booking_id)).first()
                if existing:
                    logger.info(f"Бронирование {booking_id} уже существует, пропускаем")
                    skip_count += 1
                    continue
                
                # Создаем запись
                booking = Booking(**booking_model_data)
                db.add(booking)
                db.commit()
                
                logger.success(
                    f"Создано бронирование {booking_id}: "
                    f"{booking_model_data['apartment_title']} | "
                    f"{booking_model_data['begin_date']} - {booking_model_data['end_date']} | "
                    f"{booking_model_data['client_fio']}"
                )
                success_count += 1
                
            except Exception as e:
                logger.error(f"Ошибка при обработке бронирования {booking_id}: {e}")
                error_count += 1
                db.rollback()
                continue
    
    finally:
        db.close()
    
    # Итоговая статистика
    logger.info("=" * 80)
    logger.info("Миграция завершена")
    logger.info("=" * 80)
    logger.info(f"Всего бронирований: {len(bookings_data)}")
    logger.success(f"Успешно создано: {success_count}")
    logger.warning(f"Пропущено: {skip_count}")
    logger.error(f"Ошибок: {error_count}")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        migrate_data()
    except Exception as e:
        logger.exception(f"Критическая ошибка при миграции: {e}")
        sys.exit(1)

