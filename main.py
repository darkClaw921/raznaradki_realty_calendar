"""
Точка входа для запуска приложения через uv run main.py
"""

if __name__ == "__main__":
    import uvicorn
    from loguru import logger
    
    logger.info("Запуск сервера через uv run main.py")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

