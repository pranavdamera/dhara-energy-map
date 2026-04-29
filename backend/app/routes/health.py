from fastapi import APIRouter
from sqlalchemy import text

from backend.app.db import engine

router = APIRouter()


@router.get("/health")
def health():
    status = {"status": "ok", "db": "unknown"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as exc:  # pragma: no cover - operational check
        status["db"] = f"error: {exc}"
    return status
