"""
Миграция: добавление полей platform_tax и balance_to_be_paid_1 в таблицу bookings

Добавляет два новых поля:
- platform_tax: комиссия площадки (Numeric(10,2), nullable)
- balance_to_be_paid_1: доплата (Numeric(10,2), nullable)

Эти поля используются для расчета разнарядок:
- Общая сумма = amount - platform_tax
- Предоплата = prepayment - platform_tax
- Доплата = balance_to_be_paid_1

Запуск: uv run python migrate/add_platform_tax_fields.py
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импорта модулей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, create_engine
from loguru import logger
from app.config import get_settings
from datetime import datetime


# Настройка логирования
log_file = f"logs/migration_platform_tax_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logger.add(
    log_file,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    level="INFO"
)


def check_column_exists(conn, column_name: str) -> bool:
    """Проверяет существование колонки в таблице bookings"""
    check_sql = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'bookings' 
        AND column_name = :column_name
    """)
    result = conn.execute(check_sql, {"column_name": column_name}).fetchone()
    return result is not None


def add_platform_tax_fields():
    """
    Добавить поля platform_tax и balance_to_be_paid_1 в таблицу bookings
    """
    logger.info("=" * 60)
    logger.info("Начало миграции: добавление platform_tax и balance_to_be_paid_1")
    logger.info("=" * 60)
    
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # Проверяем существование полей
            platform_tax_exists = check_column_exists(conn, "platform_tax")
            balance_exists = check_column_exists(conn, "balance_to_be_paid_1")
            
            logger.info(f"platform_tax существует: {platform_tax_exists}")
            logger.info(f"balance_to_be_paid_1 существует: {balance_exists}")
            
            # Добавляем platform_tax если не существует
            if not platform_tax_exists:
                logger.info("Добавление поля platform_tax...")
                alter_sql = text("""
                    ALTER TABLE bookings 
                    ADD COLUMN platform_tax NUMERIC(10, 2)
                """)
                conn.execute(alter_sql)
                conn.commit()
                logger.success("✓ Поле platform_tax успешно добавлено")
            else:
                logger.info("Поле platform_tax уже существует, пропускаем")
            
            # Добавляем balance_to_be_paid_1 если не существует
            if not balance_exists:
                logger.info("Добавление поля balance_to_be_paid_1...")
                alter_sql = text("""
                    ALTER TABLE bookings 
                    ADD COLUMN balance_to_be_paid_1 NUMERIC(10, 2)
                """)
                conn.execute(alter_sql)
                conn.commit()
                logger.success("✓ Поле balance_to_be_paid_1 успешно добавлено")
            else:
                logger.info("Поле balance_to_be_paid_1 уже существует, пропускаем")
            
            # Проверяем результат
            platform_tax_exists_after = check_column_exists(conn, "platform_tax")
            balance_exists_after = check_column_exists(conn, "balance_to_be_paid_1")
            
            if platform_tax_exists_after and balance_exists_after:
                logger.success("✓ Миграция выполнена успешно")
                return True
            else:
                logger.error("✗ Ошибка: миграция не применилась корректно")
                return False
                
    except Exception as e:
        logger.error(f"✗ Ошибка миграции: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Запуск скрипта миграции platform_tax и balance_to_be_paid_1")
    
    success = add_platform_tax_fields()
    
    if success:
        logger.success("=" * 60)
        logger.success("Миграция завершена успешно")
        logger.success("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("Миграция завершена с ошибками")
        logger.error("=" * 60)
        sys.exit(1)
