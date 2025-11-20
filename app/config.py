from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from datetime import datetime

class Settings(BaseSettings):
    """Настройки приложения из .env файла"""
    database_url: str
    admin_username: str = "admin"
    admin_password: str = "admin"
    user_username: str = "user"
    user_password: str = "user"
    secret_key: str
    
    # Дата истечения срока действия авторизации для администраторов
    admin_expiration_date: Optional[datetime] = None
    
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