from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


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
    subject: str
    description: str
    category_id: Optional[int] = None


class TicketOut(BaseModel):
    """Поля status/status_label/category_name/... берутся из ORM-модели."""

    model_config = ConfigDict(from_attributes=True)

    number: str
    subject: str
    description: str
    created_at: datetime
    status: str                     # код: new / in_work / done / closed
    status_label: str               # на русском: Новая / В работе / ...
    category_name: Optional[str] = None
    executor_name: Optional[str] = None
    applicant_name: Optional[str] = None
    comments: List[CommentOut] = []


class TicketPatch(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None     # у заявителя дополняет, у оператора/админа заменяет
    category_id: Optional[int] = None
    executor_id: Optional[int] = None
    status: Optional[str] = None
    comment: Optional[str] = None         # комментарий к изменению


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
