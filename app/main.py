from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.database import init_db
from app.routers import webhook, web, payments, services
from prometheus_fastapi_instrumentator import Instrumentator
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


# Обработчик ошибок валидации для детального логирования
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Логирование ошибок валидации запросов"""
    logger.error("=" * 80)
    logger.error("ОШИБКА ВАЛИДАЦИИ ЗАПРОСА (422)")
    logger.error(f"URL: {request.method} {request.url}")
    logger.error(f"Client: {request.client.host if request.client else 'Unknown'}")
    
    # Логируем детали ошибок валидации
    logger.error("Детали ошибок валидации:")
    for error in exc.errors():
        logger.error(f"  - Поле: {' -> '.join(str(loc) for loc in error['loc'])}")
        logger.error(f"    Тип: {error['type']}")
        logger.error(f"    Сообщение: {error['msg']}")
        if 'input' in error:
            logger.error(f"    Входное значение: {error['input']}")
    
    # Пытаемся получить body запроса
    try:
        body = await request.body()
        logger.error(f"Request body (raw): {body.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.error(f"Не удалось прочитать body: {e}")
    
    # Логируем form data если есть
    try:
        form = await request.form()
        logger.error("Form data:")
        for key, value in form.items():
            logger.error(f"  {key}: '{value}' (type: {type(value).__name__})")
    except Exception as e:
        logger.error(f"Не удалось прочитать form data: {e}")
    
    logger.error("=" * 80)
    
    # Безопасная сериализация body для ответа
    try:
        body_str = str(exc.body) if exc.body else None
    except:
        body_str = None
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "message": "Ошибка валидации данных"
        }
    )


Instrumentator().instrument(app).expose(app)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение роутеров
app.include_router(webhook.router)
app.include_router(web.router)
app.include_router(payments.router)
app.include_router(services.router)


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

