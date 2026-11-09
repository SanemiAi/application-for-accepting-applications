from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import Priority, Status


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: Optional[str] = None
    role: str


class RegisterIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    created_at: datetime
    author_name: Optional[str] = None


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200, description="Тема заявки, от 3 символов")
    description: str = Field(min_length=1, max_length=10000, description="Описание проблемы")
    category_id: Optional[int] = Field(default=None, ge=1)
    priority: str = Field(default=Priority.MEDIUM, description="low / medium / high")

    @field_validator("priority")
    @classmethod
    def _check_priority(cls, v: str) -> str:
        if v not in Priority.ALL:
            raise ValueError(f"Приоритет должен быть одним из: {', '.join(Priority.ALL)}")
        return v


class TicketOut(BaseModel):
    """Поля status/status_label/category_name/... берутся из ORM-модели."""

    model_config = ConfigDict(from_attributes=True)

    number: str
    subject: str
    description: str
    created_at: datetime
    status: str                     # код: new / in_work / done / closed
    status_label: str               # на русском: Новая / В работе / ...
    priority: str                   # код: low / medium / high
    priority_label: str             # на русском: Низкий / Средний / Высокий
    category_name: Optional[str] = None
    executor_name: Optional[str] = None
    applicant_name: Optional[str] = None
    comments: List[CommentOut] = []


class TicketPatch(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1, max_length=10000)  # у заявителя дополняет, у оператора/админа заменяет
    category_id: Optional[int] = Field(default=None, ge=1)
    executor_id: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = None
    priority: Optional[str] = None
    comment: Optional[str] = Field(default=None, max_length=2000)  # комментарий к изменению

    @field_validator("priority")
    @classmethod
    def _check_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in Priority.ALL:
            raise ValueError(f"Приоритет должен быть одним из: {', '.join(Priority.ALL)}")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in Status.ALL:
            raise ValueError(f"Статус должен быть одним из: {', '.join(Status.ALL)}")
        return v


class CommentCreate(BaseModel):
    text: str


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "applicant"


class UserPatch(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
