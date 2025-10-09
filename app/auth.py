from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config import get_settings
import secrets

security = HTTPBasic()
settings = get_settings()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    Проверка учетных данных через HTTP Basic Auth
    """
    correct_username = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


def get_current_user_from_session(request: Request):
    """
    Проверка аутентификации через session cookie
    Примечание: для веб-страниц используйте check_auth() из web.py,
    эта функция предназначена для API endpoints и возвращает JSON ошибку
    """
    session_token = request.cookies.get("session_token")
    if not session_token or session_token != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    return True


def create_session_cookie(response: Response):
    """
    Создание session cookie после успешной аутентификации
    """
    response.set_cookie(
        key="session_token",
        value=settings.secret_key,
        httponly=True,
        max_age=86400,  # 24 часа
        samesite="lax"
    )

