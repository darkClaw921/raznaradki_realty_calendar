"""
Скрипт миграции для добавления индексов в БД для оптимизации производительности

Добавляет индексы на поля:
- bookings.apartment_title
- bookings.is_delete

Запуск: uv run python add_indexes_migration.py
"""

from sqlalchemy import create_engine, text
from loguru import logger
import sys
from app.config import get_settings

# Настройка логирования
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/migration_indexes.log", rotation="10 MB", retention="30 days", level="DEBUG")


def add_indexes():
    """Добавить индексы в БД если их еще нет"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    logger.info("Начало миграции индексов...")
    
    with engine.connect() as conn:
        # Проверяем и создаем индекс на apartment_title
        try:
            logger.info("Проверка индекса ix_bookings_apartment_title...")
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'bookings' AND indexname = 'ix_bookings_apartment_title';
            """))
            
            if result.fetchone():
                logger.info("✓ Индекс ix_bookings_apartment_title уже существует")
            else:
                logger.info("Создание индекса ix_bookings_apartment_title...")
                conn.execute(text("""
                    CREATE INDEX ix_bookings_apartment_title ON bookings (apartment_title);
                """))
                conn.commit()
                logger.info("✓ Индекс ix_bookings_apartment_title создан")
        except Exception as e:
            logger.error(f"Ошибка при работе с индексом ix_bookings_apartment_title: {e}")
            conn.rollback()
        
        # Проверяем и создаем индекс на is_delete
        try:
            logger.info("Проверка индекса ix_bookings_is_delete...")
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'bookings' AND indexname = 'ix_bookings_is_delete';
            """))
            
            if result.fetchone():
                logger.info("✓ Индекс ix_bookings_is_delete уже существует")
            else:
                logger.info("Создание индекса ix_bookings_is_delete...")
                conn.execute(text("""
                    CREATE INDEX ix_bookings_is_delete ON bookings (is_delete);
                """))
                conn.commit()
                logger.info("✓ Индекс ix_bookings_is_delete создан")
        except Exception as e:
            logger.error(f"Ошибка при работе с индексом ix_bookings_is_delete: {e}")
            conn.rollback()
    
    logger.info("Миграция индексов завершена!")
    logger.info("Все индексы успешно созданы. Производительность запросов должна улучшиться.")


if __name__ == "__main__":
    try:
        add_indexes()
    except Exception as e:
        logger.error(f"Критическая ошибка при миграции: {e}")
        sys.exit(1)

