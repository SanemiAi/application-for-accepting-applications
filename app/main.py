import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import Base, engine, SessionLocal
from . import models
from .auth import hash_password
from .routers import admin_router, auth_router, tickets_router, web_router

app = FastAPI(title="Система приёма и подачи заявок", version="1.0.0")

# REST API — под префиксом /api, веб-интерфейс — в корне (во избежание конфликта маршрутов)
app.include_router(auth_router.router, prefix="/api")
app.include_router(tickets_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")
app.include_router(web_router.router)  # веб-интерфейс (браузер)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _wants_html(request: Request) -> bool:
    """Браузерные страницы (не /api) получают HTML-страницу ошибки."""
    return not request.url.path.startswith("/api")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if _wants_html(request) and exc.status_code in (403, 404, 405, 500):
        messages = {
            403: "Нет доступа к этой странице.",
            404: "Страница или заявка не найдена.",
            405: "Действие не поддерживается.",
            500: "Внутренняя ошибка сервера.",
        }
        return templates.TemplateResponse(
            request, "error.html",
            {"user": None, "role_label": "", "code": exc.status_code,
             "message": messages[exc.status_code], "detail": str(exc.detail)},
            status_code=exc.status_code,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Единый формат ошибки валидации для API (HTTP 422)."""
    errors = [
        {"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "message": e.get("msg", "")}
        for e in exc.errors()
    ]
    return JSONResponse(
        {"detail": "Ошибка валидации данных", "errors": errors}, status_code=422
    )


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _migrate()
    db = SessionLocal()
    try:
        # Стартовый администратор (задаётся через переменные окружения)
        if not db.query(models.User).filter_by(role=models.Role.ADMIN).first():
            admin = models.User(
                username=os.getenv("ADMIN_USERNAME", "admin"),
                password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
                full_name="Администратор",
                role=models.Role.ADMIN,
            )
            db.add(admin)
        # Стартовые категории (не менее 4 по ТЗ)
        for name in ("Техподдержка", "Снабжение", "Административный вопрос",
                     "Кадровый вопрос", "ИТ-оборудование"):
            if not db.query(models.Category).filter_by(name=name).first():
                db.add(models.Category(name=name))
        db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


def _migrate():
    """Простейшие миграции для существующей БД (ALTER TABLE при отсутствии колонки)."""
    from sqlalchemy import inspect, text
    with engine.begin() as conn:
        columns = {c["name"] for c in inspect(conn).get_columns("tickets")}
        if "priority" not in columns:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'medium'"
            ))
