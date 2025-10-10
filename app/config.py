from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения из .env файла"""
    database_url: str
    admin_username: str = "admin"
    admin_password: str = "admin"
    secret_key: str
    
    # Опциональные переменные для PostgreSQL (для docker-compose)
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    postgres_port: Optional[int] = None
    postgres_host: Optional[str] = None
    port: Optional[int]=None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки приложения (кешируется)"""
    return Settings()

