#!/usr/bin/env python3
"""
Миграция для создания таблицы expenses
"""

import sys
import os
from datetime import datetime
from loguru import logger
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Date, Numeric, DateTime
from sqlalchemy.dialects.postgresql import VARCHAR

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import Base

def main():
    """Основная функция миграции"""
    # Настройка логирования
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.add(f"logs/migration_expenses_{timestamp}.log", 
               rotation="10 MB", 
               retention="30 days", 
               compression="zip",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}")
    
    logger.info("Начало миграции: создание таблицы expenses")
    
    try:
        # Получаем настройки
        settings = get_settings()
        
        # Создаем движок базы данных
        engine = create_engine(settings.database_url)
        logger.info("Подключение к базе данных установлено")
        
        # Создаем таблицу expenses
        metadata = MetaData()
        
        expenses_table = Table(
            'expenses',
            metadata,
            Column('id', Integer, primary_key=True, index=True),
            Column('apartment_title', VARCHAR, nullable=True),
            Column('expense_date', Date, nullable=False, index=True),
            Column('amount', Numeric(10, 2), nullable=False),
            Column('category', VARCHAR, nullable=True),
            Column('comment', VARCHAR, nullable=True),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        )
        
        # Создаем таблицу
        metadata.create_all(engine)
        logger.success("Таблица expenses успешно создана")
        
        logger.info("Миграция успешно завершена")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {e}")
        raise

if __name__ == "__main__":
    main()