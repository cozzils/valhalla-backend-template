"""
Modelli del database — tabelle per le funzionalità base dei siti Valhalla.

Contact  → form di contatto (tutti i piani)
Booking  → prenotazioni tavoli/appuntamenti (piano Business e Pro)

Per aggiungere funzionalità al piano Pro (es. catalogo prodotti, newsletter):
aggiungi nuovi modelli qui e riesegui create_tables().
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.sql import func
import enum
from database import Base


class BookingStatus(str, enum.Enum):
    pending = "pending"       # in attesa di conferma
    confirmed = "confirmed"   # confermata dal titolare
    cancelled = "cancelled"   # annullata


class Contact(Base):
    """
    Messaggi ricevuti dal form di contatto del sito.
    Usato in tutti e tre i piani (Starter, Business, Pro).
    """
    __tablename__ = "contacts"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(150), nullable=False)
    phone      = Column(String(20), nullable=True)
    message    = Column(Text, nullable=False)
    is_read    = Column(Boolean, default=False)           # il titolare ha letto il messaggio?
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Campo opzionale: identifica a quale cliente Valhalla appartiene questo DB
    # Utile se usi un DB condiviso per più clienti piccoli
    client_slug = Column(String(50), nullable=True)


class Booking(Base):
    """
    Prenotazioni tavoli / appuntamenti / servizi.
    Attivo nei piani Business e Pro.
    Adattabile a: ristoranti, parrucchieri, studi medici, officine, ecc.
    """
    __tablename__ = "bookings"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(150), nullable=False)
    phone         = Column(String(20), nullable=False)   # obbligatorio per prenotazioni
    date          = Column(String(20), nullable=False)   # es. "2024-12-25"
    time          = Column(String(10), nullable=False)   # es. "20:00"
    party_size    = Column(Integer, nullable=True)        # numero persone (ristoranti)
    notes         = Column(Text, nullable=True)           # richieste speciali
    status        = Column(
        Enum(BookingStatus),
        default=BookingStatus.pending,
        nullable=False
    )
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    client_slug   = Column(String(50), nullable=True)
