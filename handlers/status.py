"""Handler per /stato e visualizzazione stato strada."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
from services.alerts import AlertService

logger = logging.getLogger(__name__)


def _build_keyboard(alerts: list[dict]) -> InlineKeyboardMarkup:
    """Costruisce la tastiera con i pulsanti per ogni segnalazione."""
    keyboard_rows = []

    for alert in alerts:
        alert_id = alert["id"]
        tipo_short = alert["tipo"][:12]
        keyboard_rows.append([
            InlineKeyboardButton(f"🔴 Ancora presente ({tipo_short})", callback_data=f"confirm_{alert_id}"),
            InlineKeyboardButton("🟢 Strada libera", callback_data=f"resolve_status_{alert_id}")
        ])

    keyboard_rows.append([
        InlineKeyboardButton("🔄 Aggiorna", callback_data="check_status"),
        InlineKeyboardButton("🏠 Menu",     callback_data="menu")
    ])

    return InlineKeyboardMarkup(keyboard_rows)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il comando /stato."""
    alerts = await db.get_active_alerts()
    message = AlertService.format_status_message(alerts)
    keyboard = _build_keyboard(alerts)

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
    keyboard = _build_keyboard(alerts)

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# Handler da esportare
status_handler = CommandHandler("stato", status_command)
status_callback_handler = CallbackQueryHandler(check_status_callback, pattern=r"^check_status$")