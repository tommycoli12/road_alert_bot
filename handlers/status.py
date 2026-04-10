"""Handler per /stato e visualizzazione stato strada."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
from services.alerts import AlertService

logger = logging.getLogger(__name__)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il comando /stato."""
    alerts = await db.get_active_alerts()
    message = AlertService.format_status_message(alerts)
    
    # Costruisce i bottoni per ogni segnalazione attiva
    keyboard_rows = []
    
    for alert in alerts:
        alert_id = alert["id"]
        tipo_short = alert["tipo"][:10]  # Abbrevia per il bottone
        keyboard_rows.append([
            InlineKeyboardButton(f"✅ Conferma {tipo_short}", callback_data=f"confirm_{alert_id}"),
            InlineKeyboardButton("🟢 Risolto", callback_data=f"resolve_{alert_id}")
        ])
    
    # Bottone per tornare al menu
    keyboard_rows.append([
        InlineKeyboardButton("🔄 Aggiorna", callback_data="check_status"),
        InlineKeyboardButton("🏠 Menu", callback_data="menu")
    ])
    
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def check_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il callback per visualizzare lo stato."""
    query = update.callback_query
    await query.answer()
    
    alerts = await db.get_active_alerts()
    message = AlertService.format_status_message(alerts)
    
    # Costruisce i bottoni
    keyboard_rows = []
    
    for alert in alerts:
        alert_id = alert["id"]
        tipo_short = alert["tipo"][:10]
        keyboard_rows.append([
            InlineKeyboardButton(f"✅ Conferma {tipo_short}", callback_data=f"confirm_{alert_id}"),
            InlineKeyboardButton("🟢 Risolto", callback_data=f"resolve_{alert_id}")
        ])
    
    keyboard_rows.append([
        InlineKeyboardButton("🔄 Aggiorna", callback_data="check_status"),
        InlineKeyboardButton("🏠 Menu", callback_data="menu")
    ])
    
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# Handler da esportare
status_handler = CommandHandler("stato", status_command)
status_callback_handler = CallbackQueryHandler(check_status_callback, pattern=r"^check_status$")
