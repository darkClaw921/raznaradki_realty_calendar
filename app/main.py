from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.database import init_db
from app.routers import webhook, web


# Настройка логирования через loguru
logger.remove()  # Удаляем стандартный обработчик
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="DEBUG"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager для FastAPI приложения
    Выполняется при запуске и остановке приложения
    """
    # Startup
    logger.info("=" * 50)
    logger.info("Запуск приложения DMD Cottage Sheets")
    logger.info("=" * 50)
    
    try:
        logger.info("Инициализация базы данных...")
        init_db()
        logger.success("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Остановка приложения DMD Cottage Sheets")


# Создание FastAPI приложения
app = FastAPI(
    title="DMD Cottage Sheets",
    description="API для управления бронированиями недвижимости",
    version="1.0.0",
    lifespan=lifespan
)


# Подключение роутеров
app.include_router(webhook.router)
app.include_router(web.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "DMD Cottage Sheets"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск сервера через uvicorn")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        # reload=True
    )

