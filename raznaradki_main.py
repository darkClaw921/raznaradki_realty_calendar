"""
Точка входа для запуска приложения через uv run main.py
"""
from dotenv import load_dotenv
import os

load_dotenv()
PORT=int(os.getenv('PORT'))
if __name__ == "__main__":
    import uvicorn
    from loguru import logger
    
    logger.info("Запуск сервера через uv run main.py")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        workers=3,

    )

