"""
Connessione al database Neon PostgreSQL.
Funziona sia in locale (con .env) che in produzione (variabili Vercel/Render).
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL non trovata. "
        "Copia .env.example in .env e inserisci la stringa di connessione Neon."
    )

# Neon richiede SSL — SQLAlchemy lo gestisce automaticamente con ?sslmode=require
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # verifica connessione prima di usarla
    pool_recycle=300,         # ricicla connessioni ogni 5 min (utile con scale-to-zero)
    connect_args={"sslmode": "require"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency injection per FastAPI — usato nelle route con Depends(get_db)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea tutte le tabelle definite nei models. Chiamato all'avvio dell'app."""
    from models import Contact, Booking  # import qui per evitare circular imports
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelle DB verificate/create su Neon")
