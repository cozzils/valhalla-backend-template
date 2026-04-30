"""
Prenotazioni — endpoint per gestire prenotazioni tavoli/appuntamenti.
Adattabile a ristoranti, parrucchieri, studi medici, officine, ecc.

Piani supportati: Business ✅  Pro ✅  (Starter: non incluso)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import httpx

from database import get_db
from models import Booking, BookingStatus

router = APIRouter()


# ─── Schema input ─────────────────────────────────────────────────────────────
class BookingForm(BaseModel):
    name: str
    email: EmailStr
    phone: str
    date: str          # formato "YYYY-MM-DD"
    time: str          # formato "HH:MM"
    party_size: Optional[int] = None
    notes: Optional[str] = None
    client_slug: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


# ─── Endpoints ───────────────────────────────────────────────────────────────
@router.post("/booking", tags=["Prenotazioni"])
async def create_booking(form: BookingForm, db: Session = Depends(get_db)):
    """
    Crea una nuova prenotazione.
    Salva nel DB e notifica il titolare via email.
    """
    booking = Booking(
        name=form.name,
        email=form.email,
        phone=form.phone,
        date=form.date,
        time=form.time,
        party_size=form.party_size,
        notes=form.notes,
        status=BookingStatus.pending,
        client_slug=form.client_slug,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Notifica email al titolare
    await send_booking_notification(form)

    return {
        "success": True,
        "message": f"Prenotazione ricevuta per il {form.date} alle {form.time}. Ti confermeremo presto!",
        "id": booking.id,
        "status": "pending"
    }


@router.get("/bookings", tags=["Prenotazioni"])
def get_bookings(
    client_slug: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db)
):
    """
    Lista prenotazioni — per il pannello admin del cliente.
    Filtrabile per data e status.
    """
    query = db.query(Booking)

    if client_slug:
        query = query.filter(Booking.client_slug == client_slug)
    if date:
        query = query.filter(Booking.date == date)
    if status:
        query = query.filter(Booking.status == status)

    bookings = query.order_by(Booking.date, Booking.time).limit(200).all()

    return {"bookings": [
        {
            "id": b.id,
            "name": b.name,
            "email": b.email,
            "phone": b.phone,
            "date": b.date,
            "time": b.time,
            "party_size": b.party_size,
            "notes": b.notes,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bookings
    ]}


@router.patch("/bookings/{booking_id}/status", tags=["Prenotazioni"])
def update_booking_status(
    booking_id: int,
    update: BookingStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Aggiorna lo status di una prenotazione (pending → confirmed / cancelled).
    Da chiamare dal pannello admin quando il titolare gestisce le prenotazioni.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    booking.status = update.status
    db.commit()

    return {
        "success": True,
        "id": booking_id,
        "new_status": update.status
    }


# ─── Helper: email notifica prenotazione ─────────────────────────────────────
async def send_booking_notification(form: BookingForm):
    """Notifica il titolare di una nuova prenotazione via Resend."""
    resend_api_key = os.getenv("RESEND_API_KEY")
    notify_email = os.getenv("NOTIFY_EMAIL")

    if not resend_api_key or not notify_email:
        print("⚠️  RESEND_API_KEY o NOTIFY_EMAIL non configurati — email skippata")
        return

    persone = f"{form.party_size} persone" if form.party_size else "n.d."

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_api_key}"},
                json={
                    "from": "Valhalla Notifiche <notifiche@valhalla.company>",
                    "to": [notify_email],
                    "subject": f"📅 Nuova prenotazione — {form.date} alle {form.time}",
                    "html": f"""
                        <h2>Nuova prenotazione ricevuta</h2>
                        <p><strong>Nome:</strong> {form.name}</p>
                        <p><strong>Telefono:</strong> {form.phone}</p>
                        <p><strong>Email:</strong> {form.email}</p>
                        <p><strong>Data:</strong> {form.date} alle {form.time}</p>
                        <p><strong>Persone:</strong> {persone}</p>
                        <p><strong>Note:</strong> {form.notes or 'nessuna'}</p>
                        <hr>
                        <p><em>Vai nel pannello admin per confermare o annullare.</em></p>
                    """,
                },
                timeout=5.0,
            )
    except Exception as e:
        print(f"⚠️  Errore invio email prenotazione: {e}")
