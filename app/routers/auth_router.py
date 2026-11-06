from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    """Регистрация нового пользователя (по умолчанию — заявитель)."""
    if db.query(models.User).filter_by(username=data.username).first():
        raise HTTPException(400, "Пользователь с таким логином уже существует")
    user = models.User(
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=models.Role.APPLICANT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(models.User).filter_by(username=form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return schemas.TokenOut(access_token=create_access_token(user.id))
