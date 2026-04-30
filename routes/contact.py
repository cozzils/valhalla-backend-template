"""
Form di contatto — endpoint per ricevere messaggi dal sito del cliente.
Salva il messaggio su Neon e manda una email di notifica al titolare.

Piani supportati: Starter ✅  Business ✅  Pro ✅
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import httpx

from database import get_db
from models import Contact

router = APIRouter()


# ─── Schema input (validazione automatica FastAPI) ───────────────────────────
class ContactForm(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: str
    client_slug: Optional[str] = None  # identifica il sito del cliente


# ─── Endpoint ────────────────────────────────────────────────────────────────
@router.post("/contact", tags=["Contatti"])
async def submit_contact(form: ContactForm, db: Session = Depends(get_db)):
    """
    Riceve il form di contatto dal frontend e:
    1. Salva il messaggio nel DB Neon
    2. Manda email di notifica al titolare dell'attività (via Resend)
    """

    # 1. Salva nel DB
    contact = Contact(
        name=form.name,
        email=form.email,
        phone=form.phone,
        message=form.message,
        client_slug=form.client_slug,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    # 2. Manda email di notifica (via Resend — gratuito fino a 3.000/mese)
    await send_notification_email(form)

    return {
        "success": True,
        "message": "Messaggio ricevuto. Ti contatteremo presto!",
        "id": contact.id
    }


@router.get("/contacts", tags=["Contatti"])
def get_contacts(
    client_slug: Optional[str] = None,
    unread_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Lista messaggi ricevuti — da usare nel pannello admin del cliente.
    Filtra per client_slug se usi un DB condiviso.
    """
    query = db.query(Contact)

    if client_slug:
        query = query.filter(Contact.client_slug == client_slug)
    if unread_only:
        query = query.filter(Contact.is_read == False)

    contacts = query.order_by(Contact.created_at.desc()).limit(100).all()

    return {"contacts": [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "message": c.message,
            "is_read": c.is_read,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in contacts
    ]}


@router.patch("/contacts/{contact_id}/read", tags=["Contatti"])
def mark_as_read(contact_id: int, db: Session = Depends(get_db)):
    """Segna un messaggio come letto."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Messaggio non trovato")

    contact.is_read = True
    db.commit()
    return {"success": True}


# ─── Helper: invio email via Resend ─────────────────────────────────────────
async def send_notification_email(form: ContactForm):
    """
    Manda email di notifica al titolare usando Resend.
    Resend è gratuito fino a 3.000 email/mese — perfetto per piccole attività.

    Setup:
    1. Crea account su resend.com
    2. Aggiungi RESEND_API_KEY e NOTIFY_EMAIL nel .env
    """
    resend_api_key = os.getenv("RESEND_API_KEY")
    notify_email = os.getenv("NOTIFY_EMAIL")

    # Se Resend non è configurato, skippa silenziosamente (non blocca il form)
    if not resend_api_key or not notify_email:
        print("⚠️  RESEND_API_KEY o NOTIFY_EMAIL non configurati — email skippata")
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_api_key}"},
                json={
                    "from": "Valhalla Notifiche <notifiche@valhalla.company>",
                    "to": [notify_email],
                    "subject": f"📬 Nuovo messaggio da {form.name}",
                    "html": f"""
                        <h2>Nuovo messaggio dal sito</h2>
                        <p><strong>Nome:</strong> {form.name}</p>
                        <p><strong>Email:</strong> {form.email}</p>
                        <p><strong>Telefono:</strong> {form.phone or 'non fornito'}</p>
                        <p><strong>Messaggio:</strong></p>
                        <blockquote>{form.message}</blockquote>
                        <hr>
                        <small>Sito: {form.client_slug or 'non specificato'}</small>
                    """,
                },
                timeout=5.0,
            )
    except Exception as e:
        # Non bloccare il form se l'email fallisce
        print(f"⚠️  Errore invio email: {e}")
