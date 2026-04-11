"""
Bot Telegram per segnalazioni stradali in tempo reale.

Avvio: python main.py
"""

import logging
from telegram.ext import Application

from config import BOT_TOKEN, ALERT_EXPIRY_MINUTES
import database as db
from handlers import (
    start_handler,
    report_handlers,
    status_handler,
    callback_handler,
    stats_handler
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
    await db.init_db()
    logger.info("Database pronto")

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

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Handler comandi
    application.add_handler(start_handler)
    application.add_handler(status_handler)
    application.add_handler(status_callback_handler)
    application.add_handler(stats_handler)

    # Handler segnalazione (menu → tipo → zona)
    for handler in report_handlers:
        application.add_handler(handler)

    # Handler callback (conferma / risolvi / menu)
    for handler in callback_handler:
        application.add_handler(handler)

    logger.info("Bot in esecuzione. Premi Ctrl+C per fermare.")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()