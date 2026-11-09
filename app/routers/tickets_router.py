from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/tickets", tags=["Заявки"])


def get_ticket_or_404(number: str, db: Session) -> models.Ticket:
    ticket = db.query(models.Ticket).filter_by(number=number).first()
    if not ticket:
        raise HTTPException(404, f"Заявка {number} не найдена")
    return ticket


def check_access(user: models.User, ticket: models.Ticket):
    """Доступ: владелец, исполнитель, оператор, администратор."""
    allowed = (
        user.role in (models.Role.OPERATOR, models.Role.ADMIN)
        or ticket.applicant_id == user.id
        or (user.role == models.Role.EXECUTOR and ticket.executor_id == user.id)
    )
    if not allowed:
        raise HTTPException(403, "Нет доступа к этой заявке")


def apply_status(ticket: models.Ticket, new_status: str, by_role: str):
    if new_status not in models.Status.ALL:
        raise HTTPException(400, f"Неизвестный статус: {new_status}")
    allowed = models.Status.TRANSITIONS.get(ticket.status, set())
    if new_status not in allowed:
        raise HTTPException(
            400,
            f"Переход '{models.Status.LABELS[ticket.status]}' -> "
            f"'{models.Status.LABELS[new_status]}' запрещён",
        )
    if ticket.status == models.Status.NEW and new_status == models.Status.IN_WORK:
        if by_role == models.Role.EXECUTOR and ticket.executor_id is None:
            pass  # исполнитель берёт сам — executor_id выставится ниже
    ticket.status = new_status


@router.get("", response_model=list[schemas.TicketOut])
def list_tickets(
    status: str | None = Query(default=None, description="Код статуса: new/in_work/done/closed"),
    category_id: int | None = None,
    priority: str | None = Query(default=None, description="Код приоритета: low/medium/high"),
    q: str | None = Query(default=None, description="Поиск по номеру, теме и описанию"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q_ = db.query(models.Ticket)
    if user.role == models.Role.APPLICANT:
        q_ = q_.filter(models.Ticket.applicant_id == user.id)
    elif user.role == models.Role.EXECUTOR:
        q_ = q_.filter(models.Ticket.executor_id == user.id)
    if status:
        q_ = q_.filter(models.Ticket.status == status)
    if category_id:
        q_ = q_.filter(models.Ticket.category_id == category_id)
    if priority:
        q_ = q_.filter(models.Ticket.priority == priority)
    if q:
        like = f"%{q.strip()}%"
        q_ = q_.filter(
            models.Ticket.subject.ilike(like)
            | models.Ticket.number.ilike(like)
            | models.Ticket.description.ilike(like)
        )
    return q_.order_by(models.Ticket.created_at.desc()).all()


@router.post("", response_model=schemas.TicketOut, status_code=201)
def create_ticket(
    data: schemas.TicketCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == models.Role.EXECUTOR:
        raise HTTPException(403, "Исполнитель не может подавать заявки")
    if data.category_id and not db.get(models.Category, data.category_id):
        raise HTTPException(400, "Категория не найдена")
    ticket = models.Ticket(
        number="tmp",  # заменим после получения id
        subject=data.subject,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        applicant_id=user.id,
        status=models.Status.NEW,
    )
    db.add(ticket)
    db.flush()
    ticket.number = f"З-{ticket.id:06d}"
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{number}", response_model=schemas.TicketOut)
def get_ticket(
    number: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(number, db)
    check_access(user, ticket)
    return ticket


@router.patch("/{number}", response_model=schemas.TicketOut)
def update_ticket(
    number: str,
    data: schemas.TicketPatch,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(number, db)
    changed = False

    if user.role == models.Role.ADMIN:
        # Администратор может менять всё
        if data.subject is not None:
            ticket.subject = data.subject
        if data.description is not None:
            ticket.description = data.description
        if data.category_id is not None:
            if not db.get(models.Category, data.category_id):
                raise HTTPException(400, "Категория не найдена")
            ticket.category_id = data.category_id
        if data.priority is not None:
            ticket.priority = data.priority
        if data.executor_id is not None:
            ticket.executor_id = _validate_executor(db, data.executor_id)
        if data.status is not None:
            apply_status(ticket, data.status, user.role)
        changed = True
        check_access(user, ticket)

    elif user.role == models.Role.OPERATOR:
        check_access(user, ticket)
        if data.category_id is not None:
            if not db.get(models.Category, data.category_id):
                raise HTTPException(400, "Категория не найдена")
            ticket.category_id = data.category_id
            changed = True
        if data.priority is not None:
            ticket.priority = data.priority
            changed = True
        if data.executor_id is not None:
            ticket.executor_id = _validate_executor(db, data.executor_id)
            changed = True
        if data.subject is not None:
            ticket.subject = data.subject
            changed = True
        if data.description is not None:
            ticket.description = data.description
            changed = True
        if data.status is not None:
            apply_status(ticket, data.status, user.role)
            changed = True

    elif user.role == models.Role.APPLICANT:
        if ticket.applicant_id != user.id:
            raise HTTPException(403, "Нет доступа к этой заявке")
        # заявитель может только дополнять описание и комментировать
        if data.description is not None:
            ticket.description += "\n\n[Дополнено заявителем] " + data.description
            changed = True
        if data.subject is not None or data.category_id is not None \
                or data.executor_id is not None or data.status is not None \
                or data.priority is not None:
            raise HTTPException(403, "Заявитель может только дополнять описание и комментарии")

    elif user.role == models.Role.EXECUTOR:
        if ticket.executor_id != user.id:
            raise HTTPException(403, "Заявка не назначена вам")
        if data.subject is not None or data.description is not None \
                or data.category_id is not None or data.executor_id is not None \
                or data.status is not None or data.priority is not None:
            raise HTTPException(403, "Используйте действия: взять в работу, выполнить, комментарий")

    if data.comment:
        db.add(models.Comment(ticket_id=ticket.id, author_id=user.id, text=data.comment))
        changed = True

    if changed:
        db.commit()
        db.refresh(ticket)
    return ticket


def _validate_executor(db: Session, executor_id: int) -> int:
    executor = db.get(models.User, executor_id)
    if not executor or executor.role != models.Role.EXECUTOR:
        raise HTTPException(400, "Исполнитель не найден (нужен пользователь с ролью executor)")
    return executor_id


@router.post("/{number}/take", response_model=schemas.TicketOut)
def take_ticket(
    number: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Исполнитель берёт новую заявку в работу (только если ещё не назначена)."""
    if user.role != models.Role.EXECUTOR:
        raise HTTPException(403, "Только исполнитель может брать заявку в работу")
    ticket = get_ticket_or_404(number, db)
    if ticket.status != models.Status.NEW:
        raise HTTPException(400, "Взять в работу можно только новую заявку")
    ticket.executor_id = user.id
    ticket.status = models.Status.IN_WORK
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{number}/complete", response_model=schemas.TicketOut)
def complete_ticket(
    number: str,
    data: schemas.CommentCreate | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Исполнитель отмечает выполнение (статус 'В работе' -> 'Выполнена')."""
    if user.role != models.Role.EXECUTOR:
        raise HTTPException(403, "Только исполнитель может отмечать выполнение")
    ticket = get_ticket_or_404(number, db)
    if ticket.executor_id != user.id:
        raise HTTPException(403, "Заявка не назначена вам")
    if ticket.status != models.Status.IN_WORK:
        raise HTTPException(400, "Отметить выполнение можно только заявку в работе")
    ticket.status = models.Status.DONE
    if data and data.text:
        db.add(models.Comment(ticket_id=ticket.id, author_id=user.id, text=data.text))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{number}/close", response_model=schemas.TicketOut)
def close_ticket(
    number: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Закрыть выполненную заявку: оператор, администратор или заявитель-владелец."""
    ticket = get_ticket_or_404(number, db)
    is_owner_applicant = user.role == models.Role.APPLICANT and ticket.applicant_id == user.id
    if user.role not in (models.Role.OPERATOR, models.Role.ADMIN) and not is_owner_applicant:
        raise HTTPException(403, "Нет прав на закрытие заявки")
    if ticket.status != models.Status.DONE:
        raise HTTPException(400, "Закрыть можно только выполненную заявку")
    ticket.status = models.Status.CLOSED
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{number}", status_code=204)
def delete_ticket(
    number: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удаление заявки (только администратор). Комментарии удаляются каскадно."""
    if user.role != models.Role.ADMIN:
        raise HTTPException(403, "Удалять заявки может только администратор")
    ticket = get_ticket_or_404(number, db)
    db.delete(ticket)
    db.commit()


@router.post("/{number}/comments", response_model=schemas.CommentOut, status_code=201)
def add_comment(
    number: str,
    data: schemas.CommentCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(number, db)
    check_access(user, ticket)
    comment = models.Comment(ticket_id=ticket.id, author_id=user.id, text=data.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
