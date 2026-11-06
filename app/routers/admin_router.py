from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles, hash_password
from ..database import get_db

router = APIRouter(
    prefix="/admin", tags=["Администрирование"], dependencies=[Depends(require_roles(models.Role.ADMIN))]
)


# ---------- Пользователи ----------

@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db)):
    if data.role not in models.Role.ALL:
        raise HTTPException(400, f"Неизвестная роль: {data.role}")
    if db.query(models.User).filter_by(username=data.username).first():
        raise HTTPException(400, "Пользователь с таким логином уже существует")
    user = models.User(
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, data: schemas.UserPatch, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if data.role is not None:
        if data.role not in models.Role.ALL:
            raise HTTPException(400, f"Неизвестная роль: {data.role}")
        user.role = data.role
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return user


# ---------- Категории ----------

@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.id).all()


@router.post("/categories", response_model=schemas.CategoryOut, status_code=201)
def create_category(data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    if db.query(models.Category).filter_by(name=data.name).first():
        raise HTTPException(400, "Категория с таким названием уже есть")
    category = models.Category(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: int, data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    category = db.get(models.Category, category_id)
    if not category:
        raise HTTPException(404, "Категория не найдена")
    category.name = data.name
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(models.Category, category_id)
    if not category:
        raise HTTPException(404, "Категория не найдена")
    db.delete(category)
    db.commit()
