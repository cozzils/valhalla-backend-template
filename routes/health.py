from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

router = APIRouter()

@router.get("/health", tags=["Sistema"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"errore: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "message": "Valhalla Backend operativo 🔥"
    }