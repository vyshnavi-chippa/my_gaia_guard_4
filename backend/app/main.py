from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes import router as danger_zone_router
from app.core.config import settings
from app.db import Base, engine
from app.models import DangerZone, GeoEvent

app = FastAPI(title=settings.app_name)
app.include_router(danger_zone_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check() -> dict:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@app.get("/")
def root() -> dict:
    return {"message": "GaiaGuard backend is running"}
