"""Gestione database SQLite con supporto asincrono."""

import aiosqlite
import logging
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
                zona TEXT NOT NULL DEFAULT '',
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

        # Tabella conferme per utente (evita conferme multiple)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conferme_utenti (
                alert_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (alert_id, user_id)
            )
        """)

        # Tabella messaggi di notifica inviati (per aggiornarli alla risoluzione)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifiche_messaggi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL
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


async def create_alert(tipo: str, zona: str, user_id: int) -> Optional[int]:
    """
    Crea una nuova segnalazione.
    Ritorna l'ID della segnalazione o None se esiste già una attiva dello stesso tipo e zona.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Verifica duplicati (stesso tipo e stessa zona)
        cursor = await db.execute(
            "SELECT id FROM segnalazioni WHERE tipo = ? AND zona = ? AND stato = 'ATTIVO'",
            (tipo, zona)
        )
        existing = await cursor.fetchone()

        if existing:
            logger.debug(f"Segnalazione {tipo} in zona {zona} già esistente, ID: {existing[0]}")
            return None

        # Crea nuova segnalazione e registra il creatore nella stessa transazione
        cursor = await db.execute(
            "INSERT INTO segnalazioni (tipo, zona, created_by) VALUES (?, ?, ?)",
            (tipo, zona, user_id)
        )
        alert_id = cursor.lastrowid

        await db.execute(
            "INSERT OR IGNORE INTO conferme_utenti (alert_id, user_id) VALUES (?, ?)",
            (alert_id, user_id)
        )
        await db.commit()

        logger.info(f"Nuova segnalazione creata: {tipo} in {zona}, ID: {alert_id}")
        return alert_id


async def get_active_alerts() -> list[dict]:
    """Restituisce tutte le segnalazioni attive."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, tipo, zona, timestamp, conferme 
               FROM segnalazioni 
               WHERE stato = 'ATTIVO'
               ORDER BY timestamp DESC"""
        )
        rows = await cursor.fetchall()
        result = [dict(row) for row in rows]
        logger.info(f"get_active_alerts: trovate {len(result)} segnalazioni attive: {[r['id'] for r in result]}")
        return result


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


async def has_user_confirmed(alert_id: int, user_id: int) -> bool:
    """Verifica se un utente ha già confermato una segnalazione."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM conferme_utenti WHERE alert_id = ? AND user_id = ?",
            (alert_id, user_id)
        )
        return await cursor.fetchone() is not None


async def confirm_alert(alert_id: int, user_id: int) -> str:
    """
    Incrementa le conferme e aggiorna il timestamp.
    Ritorna:
      'ok'       — conferma registrata con successo
      'duplicate' — utente aveva già confermato
      'not_found' — segnalazione non trovata o non attiva
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Controlla se l'utente ha già confermato
        cursor = await db.execute(
            "SELECT 1 FROM conferme_utenti WHERE alert_id = ? AND user_id = ?",
            (alert_id, user_id)
        )
        already = await cursor.fetchone()
        if already:
            return 'duplicate'

        # Controlla che la segnalazione sia attiva
        cursor = await db.execute(
            "SELECT id FROM segnalazioni WHERE id = ? AND stato = 'ATTIVO'",
            (alert_id,)
        )
        exists = await cursor.fetchone()
        if not exists:
            return 'not_found'

        # Registra la conferma dell'utente
        await db.execute(
            "INSERT INTO conferme_utenti (alert_id, user_id) VALUES (?, ?)",
            (alert_id, user_id)
        )

        # Aggiorna il conteggio e il timestamp
        await db.execute(
            """UPDATE segnalazioni 
               SET conferme = conferme + 1, timestamp = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (alert_id,)
        )
        await db.commit()

        logger.info(f"Segnalazione {alert_id} confermata da utente {user_id}")
        return 'ok'


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


async def save_notification_message(alert_id: int, chat_id: int, message_id: int) -> None:
    """Salva il riferimento a un messaggio di notifica inviato."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO notifiche_messaggi (alert_id, chat_id, message_id) VALUES (?, ?, ?)",
            (alert_id, chat_id, message_id)
        )
        await db.commit()


async def get_notification_messages(alert_id: int) -> list[dict]:
    """Restituisce tutti i messaggi di notifica inviati per una segnalazione."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT chat_id, message_id FROM notifiche_messaggi WHERE alert_id = ?",
            (alert_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def cleanup_expired_alerts() -> int:
    """
    Risolve automaticamente le segnalazioni scadute.
    Ritorna il numero di segnalazioni pulite.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """UPDATE segnalazioni 
               SET stato = 'RISOLTO'
               WHERE stato = 'ATTIVO'
               AND (strftime('%s', 'now') - strftime('%s', timestamp)) > ?""",
            (ALERT_EXPIRY_MINUTES * 60,)
        )
        await db.commit()

        count = cursor.rowcount
        if count > 0:
            logger.info(f"Pulizia automatica: {count} segnalazioni scadute")
        return count