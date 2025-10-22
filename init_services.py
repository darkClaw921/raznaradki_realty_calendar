"""
Скрипт для инициализации базовых услуг в базе данных
"""
from app.database import SessionLocal
from app.models import Service
from loguru import logger


def init_default_services():
    """Добавить базовый набор услуг"""
    db = SessionLocal()
    
    default_services = [
        "Баня",
        "Веники",
        "Доп часы",
        "Доп гости",
        "Игровая комната",
        "Спа зона",
        "Штраф",
        "Продление доп день",
        "Другие платежи"
    ]
    
    try:
        for service_name in default_services:
            # Проверяем, существует ли уже такая услуга
            existing = db.query(Service).filter(Service.name == service_name).first()
            if not existing:
                service = Service(name=service_name)
                db.add(service)
                logger.info(f"Добавлена услуга: {service_name}")
            else:
                logger.info(f"Услуга уже существует: {service_name}")
        
        db.commit()
        logger.success("Инициализация услуг завершена успешно")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при инициализации услуг: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Начало инициализации услуг...")
    init_default_services()

