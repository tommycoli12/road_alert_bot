"""Handler per /start e segnalazioni."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
from services.notifications import NotificationService
from config import ALERT_TYPES

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il comando /start."""
    user_id = update.effective_user.id
    
    # Registra l'utente
    is_new = await db.register_user(user_id)
    
    # Messaggio di benvenuto
    welcome = (
        "🛣 **Bot Segnalazioni Strada**\n\n"
        "Segnala problemi sulla strada o controlla lo stato attuale.\n\n"
        "**Cosa vuoi fare?**"
    )
    
    # Bottoni per segnalare
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚗 Incidente", callback_data="report_incidente"),
            InlineKeyboardButton("🐗 Animale", callback_data="report_animale")
        ],
        [
            InlineKeyboardButton("⛰️ Frana", callback_data="report_frana"),
            InlineKeyboardButton("⚠️ Altro", callback_data="report_altro")
        ],
        [
            InlineKeyboardButton("📊 Stato strada", callback_data="check_status")
        ]
    ])
    
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    if is_new:
        logger.info(f"Nuovo utente: {user_id}")


async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la creazione di una nuova segnalazione."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Estrae il tipo di segnalazione dal callback_data
    tipo = query.data.replace("report_", "")
    
    if tipo not in ALERT_TYPES:
        await query.edit_message_text("❌ Tipo di segnalazione non valido.")
        return
    
    # Crea la segnalazione
    alert_id = await db.create_alert(tipo, user_id)
    
    if alert_id is None:
        # Segnalazione già esistente
        tipo_display = ALERT_TYPES[tipo]
        await query.edit_message_text(
            f"⚠️ Esiste già una segnalazione attiva per:\n\n{tipo_display}\n\n"
            "Usa /stato per vedere i dettagli."
        )
        return
    
    tipo_display = ALERT_TYPES[tipo]
    
    # Conferma all'utente
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Vedi stato", callback_data="check_status"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu")
        ]
    ])
    
    await query.edit_message_text(
        f"✅ **Segnalazione inviata!**\n\n{tipo_display}\n\n"
        "Tutti gli utenti sono stati avvisati.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    # Notifica gli altri utenti
    notification_service = NotificationService(context.bot)
    await notification_service.notify_new_alert(alert_id, tipo, exclude_user=user_id)
    
    logger.info(f"Utente {user_id} ha segnalato: {tipo}")


# Handler da esportare
start_handler = CommandHandler("start", start_command)
report_handler = CallbackQueryHandler(handle_report, pattern=r"^report_")
