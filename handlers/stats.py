"""Handler per il comando /stats (solo admin)."""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import database as db

logger = logging.getLogger(__name__)

ADMIN_ID = 1050950512


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra le statistiche del bot. Riservato all'admin."""
    if update.effective_user.id != ADMIN_ID:
        return  # Ignora silenziosamente, nessun messaggio di errore

    async with __import__('aiosqlite').connect(db.DATABASE_PATH) as conn:
        # Totale utenti registrati
        cursor = await conn.execute("SELECT COUNT(*) FROM utenti")
        totale = (await cursor.fetchone())[0]

        # Utenti con notifiche attive
        cursor = await conn.execute("SELECT COUNT(*) FROM utenti WHERE notifiche_attive = 1")
        attivi = (await cursor.fetchone())[0]

        # Segnalazioni attive in questo momento
        cursor = await conn.execute("SELECT COUNT(*) FROM segnalazioni WHERE stato = 'ATTIVO'")
        segnalazioni_attive = (await cursor.fetchone())[0]

        # Totale segnalazioni di sempre
        cursor = await conn.execute("SELECT COUNT(*) FROM segnalazioni")
        segnalazioni_totali = (await cursor.fetchone())[0]

    messaggio = (
        "📊 **Statistiche Bot**\n\n"
        f"👥 Utenti registrati: **{totale}**\n"
        f"🔔 Utenti attivi (notifiche on): **{attivi}**\n"
        f"🔕 Utenti silenziati: **{totale - attivi}**\n\n"
        f"🚨 Segnalazioni ora attive: **{segnalazioni_attive}**\n"
        f"📁 Segnalazioni totali: **{segnalazioni_totali}**"
    )

    await update.message.reply_text(messaggio, parse_mode="Markdown")
    logger.info(f"Admin ha richiesto /stats")


stats_handler = CommandHandler("stats", stats_command)