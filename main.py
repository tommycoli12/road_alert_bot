"""
Bot Telegram per segnalazioni stradali in tempo reale.

Avvio: python main.py
"""

import asyncio
import logging
from telegram.ext import Application

from config import BOT_TOKEN, ALERT_EXPIRY_MINUTES
import database as db
from handlers import (
    start_handler,
    report_handler,
    status_handler,
    callback_handler
)
from handlers.status import status_callback_handler

# Configurazione logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def cleanup_job(context) -> None:
    """Job periodico per pulire le segnalazioni scadute."""
    count = await db.cleanup_expired_alerts()
    if count > 0:
        logger.info(f"Cleanup automatico: {count} segnalazioni scadute rimosse")


async def post_init(application: Application) -> None:
    """Inizializzazione post-avvio del bot."""
    # Inizializza il database
    await db.init_db()
    logger.info("Database pronto")
    
    # Schedula il job di pulizia ogni 5 minuti
    job_queue = application.job_queue
    job_queue.run_repeating(
        cleanup_job,
        interval=300,  # 5 minuti
        first=60       # Prima esecuzione dopo 1 minuto
    )
    logger.info(f"Job di pulizia schedulato (scadenza: {ALERT_EXPIRY_MINUTES} min)")


def main() -> None:
    """Avvia il bot."""
    logger.info("Avvio bot segnalazioni strada...")
    
    # Crea l'applicazione
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Registra gli handler
    application.add_handler(start_handler)
    application.add_handler(report_handler)
    application.add_handler(status_handler)
    application.add_handler(status_callback_handler)
    
    # Registra i callback handler (lista)
    for handler in callback_handler:
        application.add_handler(handler)
    
    # Avvia il bot
    logger.info("Bot in esecuzione. Premi Ctrl+C per fermare.")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
