"""
Valhalla Company — Template Backend Base
Adatto per: siti Starter / Business / Pro per attività locali
Stack: FastAPI + Neon PostgreSQL + Vercel (frontend) + Render (backend)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from database import create_tables
from routes.health import router as health_router
from routes.contact import router as contact_router
from routes.booking import router as booking_router


# ─── Startup: crea le tabelle se non esistono ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Valhalla Backend Template",
    description="Backend base per siti di attività locali",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── CORS — permetti richieste dal frontend su Vercel ───────────────────────
# In produzione sostituisci "*" con il dominio del cliente
# es: ["https://ristoranterossi.it", "https://www.ristoranterossi.it"]
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ─────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(contact_router, prefix="/api")
app.include_router(booking_router, prefix="/api")
