import os
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .. import models
from ..auth import SECRET_KEY, ALGORITHM, create_access_token, verify_password
from ..database import get_db
from .tickets_router import check_access, get_ticket_or_404

router = APIRouter(tags=["Веб-интерфейс"])

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

ROLE_LABELS = {
    models.Role.APPLICANT: "Заявитель",
    models.Role.OPERATOR: "Оператор",
    models.Role.EXECUTOR: "Исполнитель",
    models.Role.ADMIN: "Администратор",
}

COOKIE_MAX_AGE = 12 * 3600


def get_web_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """Текущий пользователь из cookie (для браузера). Возвращает None, если не авторизован."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return db.get(models.User, int(payload["sub"]))
    except (JWTError, KeyError, ValueError):
        return None


def ctx(user: models.User, **kw):
    base_ctx = {"user": user, "role_label": ROLE_LABELS[user.role]}
    base_ctx.update(kw)
    return base_ctx


# ---------- Аутентификация ----------

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Неверный логин или пароль"},
            status_code=401,
        )
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("access_token", create_access_token(user.id),
                    httponly=True, max_age=COOKIE_MAX_AGE)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# ---------- Заявки ----------

def _back(number: str, error: str | None = None) -> RedirectResponse:
    url = f"/tickets/{number}"
    if error:
        from urllib.parse import quote
        url += f"?error={quote(error)}"
    return RedirectResponse(url, status_code=303)


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    status: Optional[str] = None,
    category_id: Optional[str] = None,
    priority: Optional[str] = None,
    q: Optional[str] = None,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login")
    cat_id = None
    if category_id and category_id.strip().isdigit():
        cat_id = int(category_id)
    query = db.query(models.Ticket)
    if user.role == models.Role.APPLICANT:
        query = query.filter(models.Ticket.applicant_id == user.id)
    elif user.role == models.Role.EXECUTOR:
        query = query.filter(models.Ticket.executor_id == user.id)
    if status in models.Status.ALL:
        query = query.filter(models.Ticket.status == status)
    if cat_id:
        query = query.filter(models.Ticket.category_id == cat_id)
    if priority in models.Priority.ALL:
        query = query.filter(models.Ticket.priority == priority)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            models.Ticket.subject.ilike(like)
            | models.Ticket.number.ilike(like)
            | models.Ticket.description.ilike(like)
        )
    tickets = query.order_by(models.Ticket.created_at.desc()).all()
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse(
        request,
        "tickets.html",
        ctx(user, tickets=tickets, labels=models.Status.LABELS,
            priorities=models.Priority.LABELS,
            categories=categories, f_status=status, f_category_id=cat_id,
            f_priority=priority, f_q=q or ""),
    )


@router.get("/tickets/new", response_class=HTMLResponse)
def new_ticket_page(
    request: Request,
    error: Optional[str] = None,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login")
    if user.role == models.Role.EXECUTOR:
        raise HTTPException(403, "Исполнитель не может подавать заявки")
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse(
        request, "ticket_new.html",
        ctx(user, categories=categories, priorities=models.Priority.LABELS, error=error),
    )


@router.post("/tickets/new")
def create_ticket(
    request: Request,
    subject: str = Form(...),
    description: str = Form(...),
    category_id: Optional[int] = Form(None),
    priority: str = Form(models.Priority.MEDIUM),
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.role == models.Role.EXECUTOR:
        raise HTTPException(403, "Исполнитель не может подавать заявки")
    if len(subject.strip()) < 3:
        from urllib.parse import quote
        return RedirectResponse("/tickets/new?error=" + quote("Тема должна содержать минимум 3 символа"), status_code=303)
    if not description.strip():
        from urllib.parse import quote
        return RedirectResponse("/tickets/new?error=" + quote("Описание не может быть пустым"), status_code=303)
    if priority not in models.Priority.ALL:
        priority = models.Priority.MEDIUM
    if category_id and not db.get(models.Category, category_id):
        raise HTTPException(400, "Категория не найдена")
    ticket = models.Ticket(
        number="tmp", subject=subject.strip(), description=description.strip(),
        category_id=category_id, priority=priority,
        applicant_id=user.id, status=models.Status.NEW,
    )
    db.add(ticket)
    db.flush()
    ticket.number = f"З-{ticket.id:06d}"
    db.commit()
    return RedirectResponse(f"/tickets/{ticket.number}", status_code=303)


@router.get("/tickets/{number}", response_class=HTMLResponse)
def ticket_detail(
    request: Request,
    number: str,
    error: Optional[str] = None,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login")
    ticket = get_ticket_or_404(number, db)
    check_access(user, ticket)
    extra = {}
    if user.role in (models.Role.OPERATOR, models.Role.ADMIN):
        extra["executors"] = (
            db.query(models.User)
            .filter_by(role=models.Role.EXECUTOR)
            .order_by(models.User.full_name)
            .all()
        )
        extra["categories"] = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse(
        request,
        "ticket_detail.html",
        ctx(user, ticket=ticket, labels=models.Status.LABELS,
            priorities=models.Priority.LABELS, error=error, **extra),
    )


# ---------- Редактирование ----------

@router.get("/tickets/{number}/edit", response_class=HTMLResponse)
def edit_ticket_page(
    request: Request,
    number: str,
    error: Optional[str] = None,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login")
    ticket = get_ticket_or_404(number, db)
    check_access(user, ticket)
    if user.role == models.Role.EXECUTOR:
        raise HTTPException(403, "Исполнитель не редактирует заявку")
    categories = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse(
        request,
        "ticket_edit.html",
        ctx(user, ticket=ticket, categories=categories, labels=models.Status.LABELS,
            priorities=models.Priority.LABELS, error=error),
    )


@router.post("/tickets/{number}/edit")
def edit_ticket(
    request: Request,
    number: str,
    subject: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    priority: Optional[str] = Form(None),
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    ticket = get_ticket_or_404(number, db)
    check_access(user, ticket)

    if user.role == models.Role.APPLICANT:
        # Заявитель может только дополнять описание
        if description and description.strip():
            ticket.description += "\n\n[Дополнено заявителем] " + description.strip()
    elif user.role in (models.Role.OPERATOR, models.Role.ADMIN):
        if subject and subject.strip():
            if len(subject.strip()) < 3:
                return _back(number, "Тема должна содержать минимум 3 символа")
            ticket.subject = subject.strip()
        if description is not None and description.strip():
            ticket.description = description.strip()
        if category_id:
            if not db.get(models.Category, category_id):
                return _back(number, "Категория не найдена")
            ticket.category_id = category_id
        if priority:
            if priority not in models.Priority.ALL:
                return _back(number, "Неизвестный приоритет")
            ticket.priority = priority
    else:
        raise HTTPException(403, "Исполнитель не редактирует заявку")

    db.commit()
    return _back(number)


@router.post("/tickets/{number}/delete")
def delete_ticket_web(
    number: str,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    """Удаление заявки (только администратор, с подтверждением в интерфейсе)."""
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.role != models.Role.ADMIN:
        raise HTTPException(403, "Удалять заявки может только администратор")
    ticket = get_ticket_or_404(number, db)
    db.delete(ticket)
    db.commit()
    return RedirectResponse("/", status_code=303)


# ---------- Действия со статусами и назначением ----------

@router.post("/tickets/{number}/assign")
def assign_executor(
    number: str,
    executor_id: int = Form(...),
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.role not in (models.Role.OPERATOR, models.Role.ADMIN):
        raise HTTPException(403, "Назначать исполнителя могут оператор и администратор")
    ticket = get_ticket_or_404(number, db)
    executor = db.get(models.User, executor_id)
    if not executor or executor.role != models.Role.EXECUTOR:
        return _back(number, "Исполнитель не найден (нужен пользователь с ролью «Исполнитель»)")
    ticket.executor_id = executor_id
    db.commit()
    return _back(number)


@router.post("/tickets/{number}/take")
def web_take_ticket(
    number: str,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.role != models.Role.EXECUTOR:
        raise HTTPException(403, "Только исполнитель может брать заявку в работу")
    ticket = get_ticket_or_404(number, db)
    if ticket.status != models.Status.NEW:
        return _back(number, "Взять в работу можно только новую заявку")
    if ticket.executor_id is not None and ticket.executor_id != user.id:
        return _back(number, "Заявка уже назначена другому исполнителю")
    ticket.executor_id = user.id
    ticket.status = models.Status.IN_WORK
    db.commit()
    return _back(number)


@router.post("/tickets/{number}/complete")
def web_complete_ticket(
    number: str,
    text: Optional[str] = Form(None),
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.role != models.Role.EXECUTOR:
        raise HTTPException(403, "Только исполнитель может отмечать выполнение")
    ticket = get_ticket_or_404(number, db)
    if ticket.executor_id != user.id:
        raise HTTPException(403, "Заявка не назначена вам")
    if ticket.status != models.Status.IN_WORK:
        return _back(number, "Отметить выполнение можно только заявку в работе")
    ticket.status = models.Status.DONE
    if text and text.strip():
        db.add(models.Comment(ticket_id=ticket.id, author_id=user.id, text=text.strip()))
    db.commit()
    return _back(number)


@router.post("/tickets/{number}/close")
def web_close_ticket(
    number: str,
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    ticket = get_ticket_or_404(number, db)
    is_owner_applicant = user.role == models.Role.APPLICANT and ticket.applicant_id == user.id
    if user.role not in (models.Role.OPERATOR, models.Role.ADMIN) and not is_owner_applicant:
        raise HTTPException(403, "Нет прав на закрытие заявки")
    if ticket.status != models.Status.DONE:
        return _back(number, "Закрыть можно только выполненную заявку")
    ticket.status = models.Status.CLOSED
    db.commit()
    return _back(number)


@router.post("/tickets/{number}/comments")
def add_comment(
    request: Request,
    number: str,
    text: str = Form(...),
    user: Optional[models.User] = Depends(get_web_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    ticket = get_ticket_or_404(number, db)
    check_access(user, ticket)
    db.add(models.Comment(ticket_id=ticket.id, author_id=user.id, text=text))
    db.commit()
    return RedirectResponse(f"/tickets/{ticket.number}", status_code=303)
