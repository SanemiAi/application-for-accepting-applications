from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Role:
    APPLICANT = "applicant"   # Заявитель
    OPERATOR = "operator"     # Оператор
    EXECUTOR = "executor"     # Исполнитель
    ADMIN = "admin"           # Администратор

    ALL = (APPLICANT, OPERATOR, EXECUTOR, ADMIN)


class Status:
    NEW = "new"               # Новая
    IN_WORK = "in_work"       # В работе
    DONE = "done"             # Выполнена
    CLOSED = "closed"         # Закрыта

    LABELS = {
        NEW: "Новая",
        IN_WORK: "В работе",
        DONE: "Выполнена",
        CLOSED: "Закрыта",
    }

    ALL = tuple(LABELS)

    # Разрешённые переходы статусов
    TRANSITIONS = {
        NEW: {IN_WORK},
        IN_WORK: {DONE},
        DONE: {CLOSED},
        CLOSED: set(),
    }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(128))
    role = Column(String(20), nullable=False, default=Role.APPLICANT)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    number = Column(String(20), unique=True, nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    status = Column(String(20), nullable=False, default=Status.NEW)
    executor_id = Column(Integer, ForeignKey("users.id"))
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    category = relationship("Category")
    executor = relationship("User", foreign_keys=[executor_id])
    applicant = relationship("User", foreign_keys=[applicant_id])
    comments = relationship(
        "Comment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )

    # --- поля для сериализации ---
    @property
    def status_label(self):
        return Status.LABELS[self.status]

    @property
    def category_name(self):
        return self.category.name if self.category else None

    @property
    def executor_name(self):
        return self.executor.full_name if self.executor else None

    @property
    def applicant_name(self):
        return self.applicant.full_name if self.applicant else None


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    author = relationship("User")
    ticket = relationship("Ticket", back_populates="comments")

    @property
    def author_name(self):
        return self.author.full_name if self.author else None
