import os
from fastapi import FastAPI

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


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
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
