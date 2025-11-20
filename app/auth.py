from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config import get_settings
import secrets
from datetime import datetime

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
    
    # Проверка срока действия для администраторов
    user_type = request.cookies.get("user_type")
    if user_type == 'admin' and settings.admin_expiration_date:
        # Получаем дату создания сессии из cookie (если есть)
        session_created_str = request.cookies.get("session_created")
        if session_created_str:
            try:
                session_created = datetime.fromisoformat(session_created_str)
                # Если сессия была создана ДО даты истечения, то она недействительна
                if session_created.date() < settings.admin_expiration_date.date():
                    # Возвращаем ошибку авторизации
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Срок действия сессии истек",
                    )
                else:
                    # Если сессия была создана ПОСЛЕ даты истечения или в этот же день, то она действительна
                    return True
            except ValueError:
                pass
        
        # Если дата создания сессии не указана или не может быть распознана,
        # проверяем текущую дату (для обратной совместимости)
        if datetime.now().date() >= settings.admin_expiration_date.date():
            # Возвращаем ошибку авторизации
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Срок действия сессии истек",
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
    # Устанавливаем дату создания сессии для проверки срока действия администраторов
    response.set_cookie(
        key="session_created",
        value=datetime.now().isoformat(),
        httponly=True,
        max_age=86400,  # 24 часа
        samesite="lax"
    )