"""
Миграция: изменение поля client_id на nullable в таблице bookings

Выполняет ALTER TABLE для изменения client_id с NOT NULL на NULL.
Это необходимо для корректной обработки webhook при удалении бронирования,
где client_id может быть None.
"""
import sys
from sqlalchemy import text
from loguru import logger
from app.database import engine
from datetime import datetime


# Настройка логирования
log_file = f"logs/migration_client_id_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logger.add(
    log_file,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    level="INFO"
)


def migrate_client_id_nullable():
    """
    Изменить поле client_id на nullable в таблице bookings
    """
    logger.info("=" * 60)
    logger.info("Начало миграции: client_id nullable")
    logger.info("=" * 60)
    
    try:
        with engine.connect() as conn:
            # Проверяем, не nullable ли уже поле
            check_sql = text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'bookings' 
                AND column_name = 'client_id'
            """)
            result = conn.execute(check_sql).fetchone()
            
            if result:
                is_nullable = result[0]
                logger.info(f"Текущее состояние client_id: is_nullable = {is_nullable}")
                
                if is_nullable == 'YES':
                    logger.info("Поле client_id уже nullable, миграция не требуется")
                    return True
            
            # Изменяем колонку на nullable
            logger.info("Изменение client_id на nullable...")
            alter_sql = text("""
                ALTER TABLE bookings 
                ALTER COLUMN client_id DROP NOT NULL
            """)
            conn.execute(alter_sql)
            conn.commit()
            
            logger.success("✓ Поле client_id успешно изменено на nullable")
            
            # Проверяем результат
            result = conn.execute(check_sql).fetchone()
            if result and result[0] == 'YES':
                logger.success("✓ Миграция выполнена успешно")
                return True
            else:
                logger.error("✗ Ошибка: миграция не применилась корректно")
                return False
                
    except Exception as e:
        logger.error(f"✗ Ошибка миграции: {e}")
        return False


if __name__ == "__main__":
    logger.info("Запуск скрипта миграции client_id nullable")
    
    success = migrate_client_id_nullable()
    
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

