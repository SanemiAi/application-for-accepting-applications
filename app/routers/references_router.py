from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user, require_roles
from ..database import get_db

router = APIRouter(tags=["Справочники"])


@router.get(
    "/statuses",
    summary="Справочник статусов заявок",
    description="Возвращает все возможные статусы и допустимые переходы между ними.",
)
def list_statuses(user: models.User = Depends(get_current_user)):
    return {
        "statuses": [
            {"code": code, "label": label}
            for code, label in models.Status.LABELS.items()
        ],
        "transitions": {
            code: sorted(targets)
            for code, targets in models.Status.TRANSITIONS.items()
        },
    }


@router.get(
    "/priorities",
    summary="Справочник приоритетов",
)
def list_priorities(user: models.User = Depends(get_current_user)):
    return [
        {"code": code, "label": label}
        for code, label in models.Priority.LABELS.items()
    ]


@router.get(
    "/categories",
    response_model=list[schemas.CategoryOut],
    summary="Справочник категорий заявок",
)
def list_categories(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(models.Category).order_by(models.Category.name).all()


@router.get(
    "/users",
    response_model=list[schemas.UserOut],
    summary="Список пользователей (только администратор)",
)
def list_users(
    user: models.User = Depends(require_roles(models.Role.ADMIN)),
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.id).all()
