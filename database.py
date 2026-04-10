"""Gestione database SQLite con supporto asincrono."""

import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional
from config import DATABASE_PATH, ALERT_EXPIRY_MINUTES

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Inizializza il database e crea le tabelle se non esistono."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Tabella segnalazioni
        await db.execute("""
            CREATE TABLE IF NOT EXISTS segnalazioni (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                stato TEXT DEFAULT 'ATTIVO',
                conferme INTEGER DEFAULT 1,
                created_by INTEGER
            )
        """)
        
        # Tabella utenti
        await db.execute("""
            CREATE TABLE IF NOT EXISTS utenti (
                user_id INTEGER PRIMARY KEY,
                notifiche_attive BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indici per performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_segnalazioni_stato 
            ON segnalazioni(stato)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_segnalazioni_tipo_stato 
            ON segnalazioni(tipo, stato)
        """)
        
        await db.commit()
        logger.info("Database inizializzato con successo")


async def register_user(user_id: int) -> bool:
    """
    Registra un utente nel database.
    Ritorna True se è un nuovo utente, False se esisteva già.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM utenti WHERE user_id = ?",
            (user_id,)
        )
        exists = await cursor.fetchone()
        
        if not exists:
            await db.execute(
                "INSERT INTO utenti (user_id) VALUES (?)",
                (user_id,)
            )
            await db.commit()
            logger.info(f"Nuovo utente registrato: {user_id}")
            return True
        return False


async def get_subscribed_users() -> list[int]:
    """Restituisce lista di user_id con notifiche attive."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM utenti WHERE notifiche_attive = 1"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def create_alert(tipo: str, user_id: int) -> Optional[int]:
    """
    Crea una nuova segnalazione.
    Ritorna l'ID della segnalazione o None se esiste già una attiva dello stesso tipo.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Verifica duplicati
        cursor = await db.execute(
            "SELECT id FROM segnalazioni WHERE tipo = ? AND stato = 'ATTIVO'",
            (tipo,)
        )
        existing = await cursor.fetchone()
        
        if existing:
            logger.debug(f"Segnalazione {tipo} già esistente, ID: {existing[0]}")
            return None
        
        # Crea nuova segnalazione
        cursor = await db.execute(
            """INSERT INTO segnalazioni (tipo, created_by) 
               VALUES (?, ?)""",
            (tipo, user_id)
        )
        await db.commit()
        
        alert_id = cursor.lastrowid
        logger.info(f"Nuova segnalazione creata: {tipo}, ID: {alert_id}")
        return alert_id


async def get_active_alerts() -> list[dict]:
    """Restituisce tutte le segnalazioni attive."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, tipo, timestamp, conferme 
               FROM segnalazioni 
               WHERE stato = 'ATTIVO'
               ORDER BY timestamp DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_alert_by_id(alert_id: int) -> Optional[dict]:
    """Restituisce una segnalazione specifica."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM segnalazioni WHERE id = ?",
            (alert_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def confirm_alert(alert_id: int) -> bool:
    """
    Incrementa le conferme e aggiorna il timestamp.
    Ritorna True se l'operazione ha avuto successo.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """UPDATE segnalazioni 
               SET conferme = conferme + 1, timestamp = CURRENT_TIMESTAMP
               WHERE id = ? AND stato = 'ATTIVO'""",
            (alert_id,)
        )
        await db.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Segnalazione {alert_id} confermata")
        return success


async def resolve_alert(alert_id: int) -> bool:
    """
    Risolve una segnalazione (cambia stato in RISOLTO).
    Ritorna True se l'operazione ha avuto successo.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """UPDATE segnalazioni 
               SET stato = 'RISOLTO'
               WHERE id = ? AND stato = 'ATTIVO'""",
            (alert_id,)
        )
        await db.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Segnalazione {alert_id} risolta")
        return success


async def resolve_alerts_by_type(tipo: str) -> int:
    """
    Risolve tutte le segnalazioni attive di un certo tipo.
    Ritorna il numero di segnalazioni risolte.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """UPDATE segnalazioni 
               SET stato = 'RISOLTO'
               WHERE tipo = ? AND stato = 'ATTIVO'""",
            (tipo,)
        )
        await db.commit()
        
        count = cursor.rowcount
        if count > 0:
            logger.info(f"Risolte {count} segnalazioni di tipo {tipo}")
        return count


async def cleanup_expired_alerts() -> int:
    """
    Risolve automaticamente le segnalazioni scadute.
    Ritorna il numero di segnalazioni pulite.
    """
    expiry_time = datetime.utcnow() - timedelta(minutes=ALERT_EXPIRY_MINUTES)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """UPDATE segnalazioni 
               SET stato = 'RISOLTO'
               WHERE stato = 'ATTIVO' AND timestamp < ?""",
            (expiry_time.isoformat(),)
        )
        await db.commit()
        
        count = cursor.rowcount
        if count > 0:
            logger.info(f"Pulizia automatica: {count} segnalazioni scadute")
        return count
