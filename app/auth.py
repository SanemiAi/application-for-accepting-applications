import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .database import get_db
from . import models

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    claims = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    exc = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Не удалось проверить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise exc
    user = db.get(models.User, user_id)
    if user is None:
        raise exc
    return user


def require_roles(*roles):
    """Зависимость: текущий пользователь должен иметь одну из указанных ролей."""

    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Недостаточно прав для этого действия"
            )
        return user

    return dependency
