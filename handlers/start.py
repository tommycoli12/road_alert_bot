"""Handler per /start e segnalazioni."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
from services.notifications import NotificationService
from config import ALERT_TYPES, ALERT_ZONES

logger = logging.getLogger(__name__)


def _main_keyboard() -> InlineKeyboardMarkup:
    """Restituisce la tastiera principale con il solo pulsante di segnalazione."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Fai Segnalazione", callback_data="open_report_menu")],
        [InlineKeyboardButton("📊 Stato strada", callback_data="check_status")],
    ])


def _report_type_keyboard() -> InlineKeyboardMarkup:
    """Tastiera per la scelta del tipo di segnalazione."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚗 Incidente",       callback_data="report_type_incidente"),
            InlineKeyboardButton("🐗 Animale",          callback_data="report_type_animale"),
        ],
        [
            InlineKeyboardButton("⛰️ Frana",            callback_data="report_type_frana"),
            InlineKeyboardButton("🚔 Posto di blocco",  callback_data="report_type_posto_blocco"),
        ],
        [
            InlineKeyboardButton("🚘 Macchina ferma",   callback_data="report_type_macchina_ferma"),
            InlineKeyboardButton("🌊 Strada allagata",  callback_data="report_type_strada_allagata"),
        ],
        [
            InlineKeyboardButton("🦺 Lavori in corso",  callback_data="report_type_lavori"),
            InlineKeyboardButton("🧊 Ghiaccio",         callback_data="report_type_ghiaccio"),
        ],
        [
            InlineKeyboardButton("🌫️ Nebbia",           callback_data="report_type_nebbia"),
        ],
        [
            InlineKeyboardButton("🏠 Menu",             callback_data="menu"),
        ],
    ])


def _zone_keyboard(tipo: str) -> InlineKeyboardMarkup:
    """Tastiera per la scelta della zona, passando il tipo già selezionato."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚏 Fermata bus Segni", callback_data=f"report_zone_{tipo}_fermata_bus_segni")],
        [InlineKeyboardButton("↩️ Curva a Ceci",       callback_data=f"report_zone_{tipo}_curva_ceci")],
        [InlineKeyboardButton("📍 Metà strada",         callback_data=f"report_zone_{tipo}_meta_strada")],
        [InlineKeyboardButton("⛪ Chiesetta",            callback_data=f"report_zone_{tipo}_chiesetta")],
        [InlineKeyboardButton("🎡 Piroland",             callback_data=f"report_zone_{tipo}_piroland")],
        [InlineKeyboardButton("⛏️ Cava",                callback_data=f"report_zone_{tipo}_cava")],
        [InlineKeyboardButton("🚦 Semaforo Murillo",    callback_data=f"report_zone_{tipo}_semaforo_murillo")],
        [InlineKeyboardButton("⬅️ Indietro",            callback_data="open_report_menu")],
    ])


def _confirm_keyboard(tipo: str, zona: str) -> InlineKeyboardMarkup:
    """Tastiera per il riepilogo prima dell'invio."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Invia segnalazione", callback_data=f"report_send_{tipo}_{zona}")],
        [InlineKeyboardButton("✏️ Modifica",           callback_data="open_report_menu")],
        [InlineKeyboardButton("🏠 Menu",               callback_data="menu")],
    ])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il comando /start."""
    user_id = update.effective_user.id
    is_new = await db.register_user(user_id)

    welcome = (
        "🛣 **Bot Segnalazioni Strada**\n\n"
        "Segnala problemi sulla strada o controlla lo stato attuale.\n\n"
        "**Cosa vuoi fare?**"
    )

    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=_main_keyboard()
    )

    if is_new:
        logger.info(f"Nuovo utente: {user_id}")


async def handle_open_report_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra il menu di scelta del tipo di segnalazione."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📣 **Nuova Segnalazione**\n\nSeleziona il tipo di problema:",
        parse_mode="Markdown",
        reply_markup=_report_type_keyboard()
    )


async def handle_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la scelta del tipo: mostra la selezione zona."""
    query = update.callback_query
    await query.answer()

    tipo = query.data.replace("report_type_", "")

    if tipo not in ALERT_TYPES:
        await query.edit_message_text("❌ Tipo di segnalazione non valido.")
        return

    tipo_display = ALERT_TYPES[tipo]

    await query.edit_message_text(
        f"📣 **Nuova Segnalazione — {tipo_display}**\n\nDove si trova il problema?",
        parse_mode="Markdown",
        reply_markup=_zone_keyboard(tipo)
    )


async def handle_report_zone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la scelta della zona: mostra il riepilogo prima dell'invio."""
    query = update.callback_query
    await query.answer()

    # callback_data formato: "report_zone_<tipo>_<zona>"
    payload = query.data.replace("report_zone_", "")

    tipo = None
    zona = None
    for t in ALERT_TYPES:
        prefix = f"{t}_"
        if payload.startswith(prefix):
            tipo = t
            zona = payload[len(prefix):]
            break

    if not tipo or zona not in ALERT_ZONES:
        await query.edit_message_text("❌ Selezione non valida.")
        return

    tipo_display = ALERT_TYPES[tipo]
    zona_display = ALERT_ZONES[zona]

    await query.edit_message_text(
        f"📋 **Riepilogo segnalazione**\n\n"
        f"Tipo:  {tipo_display}\n"
        f"Zona:  {zona_display}\n\n"
        "Vuoi inviare la segnalazione?",
        parse_mode="Markdown",
        reply_markup=_confirm_keyboard(tipo, zona)
    )


async def handle_report_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Conferma definitiva: crea la segnalazione e notifica gli utenti."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # callback_data formato: "report_send_<tipo>_<zona>"
    payload = query.data.replace("report_send_", "")

    tipo = None
    zona = None
    for t in ALERT_TYPES:
        prefix = f"{t}_"
        if payload.startswith(prefix):
            tipo = t
            zona = payload[len(prefix):]
            break

    if not tipo or zona not in ALERT_ZONES:
        await query.edit_message_text("❌ Selezione non valida.")
        return

    tipo_display = ALERT_TYPES[tipo]
    zona_display = ALERT_ZONES[zona]

    # Crea la segnalazione
    alert_id = await db.create_alert(tipo, zona, user_id)

    if alert_id is None:
        await query.edit_message_text(
            f"⚠️ Esiste già una segnalazione attiva:\n\n"
            f"{tipo_display}\n{zona_display}\n\n"
            "Usa il pulsante Stato strada per i dettagli.",
            reply_markup=_main_keyboard()
        )
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Ancora presente", callback_data=f"confirm_{alert_id}"),
            InlineKeyboardButton("🟢 Strada libera",   callback_data=f"resolve_{alert_id}")
        ]
    ])

    sent = await query.edit_message_text(
        f"✅ **Segnalazione inviata!**\n\n{tipo_display}\n{zona_display}\n\n"
        "Tutti gli utenti sono stati avvisati.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    # Salva il messaggio del creatore così può essere aggiornato alla risoluzione
    if sent:
        await db.save_notification_message(alert_id, sent.chat.id, sent.message_id)

    # Notifica gli altri utenti
    notification_service = NotificationService(context.bot)
    await notification_service.notify_new_alert(alert_id, tipo, zona, exclude_user=user_id)

    logger.info(f"Utente {user_id} ha segnalato: {tipo} in {zona}")


# Handler da esportare
start_handler = CommandHandler("start", start_command)
report_handlers = [
    CallbackQueryHandler(handle_open_report_menu, pattern=r"^open_report_menu$"),
    CallbackQueryHandler(handle_report_type,      pattern=r"^report_type_"),
    CallbackQueryHandler(handle_report_zone,      pattern=r"^report_zone_"),
    CallbackQueryHandler(handle_report_send,      pattern=r"^report_send_"),
]