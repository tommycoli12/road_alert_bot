"""Handler per i callback delle interazioni con segnalazioni."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
from services.alerts import AlertService
from services.notifications import NotificationService
from config import ALERT_TYPES

logger = logging.getLogger(__name__)


def _alert_keyboard(alert_id: int) -> InlineKeyboardMarkup:
    """Tastiera standard per una segnalazione attiva."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Ancora presente", callback_data=f"confirm_{alert_id}"),
            InlineKeyboardButton("🟢 Strada libera",   callback_data=f"resolve_{alert_id}")
        ]
    ])


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la conferma di una segnalazione (una sola volta per utente)."""
    query = update.callback_query
    user_id = update.effective_user.id

    alert_id = int(query.data.replace("confirm_", ""))

    result = await db.confirm_alert(alert_id, user_id)

    if result == 'duplicate':
        await query.answer("⚠️ Hai già confermato questa segnalazione.", show_alert=True)
        return

    if result == 'not_found':
        await query.answer("⚠️ Segnalazione non più attiva.", show_alert=True)
        return

    # result == 'ok'
    await query.answer("✅ Conferma registrata!")

    # Aggiorna il messaggio con i nuovi dati
    alert = await db.get_alert_by_id(alert_id)
    if alert and alert["stato"] == "ATTIVO":
        tipo_display = ALERT_TYPES.get(alert["tipo"], "⚠️")
        zona_display = alert.get("zona", "")
        time_ago = AlertService.format_time_ago(alert["timestamp"])
        conferme = alert["conferme"]

        message = (
            f"🚨 **SEGNALAZIONE ATTIVA**\n\n"
            f"{tipo_display}\n"
            f"📍 {zona_display}\n"
            f"⏱ Aggiornato: {time_ago}\n"
            f"👥 {conferme} conferme"
        )

        try:
            await query.edit_message_text(
                message,
                parse_mode="Markdown",
                reply_markup=_alert_keyboard(alert_id)
            )
        except Exception:
            pass  # Il messaggio potrebbe essere già stato modificato


async def handle_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la risoluzione di una segnalazione."""
    query = update.callback_query

    alert_id = int(query.data.replace("resolve_", ""))

    alert = await db.get_alert_by_id(alert_id)

    if not alert or alert["stato"] != "ATTIVO":
        await query.answer("⚠️ Segnalazione già risolta", show_alert=True)
        return

    tipo = alert["tipo"]
    zona = alert.get("zona", "")

    success = await db.resolve_alert(alert_id)

    if success:
        await query.answer("🟢 Segnalazione risolta!")

        tipo_display = ALERT_TYPES.get(tipo, "⚠️")
        zona_display = alert.get("zona", "")
        testo_risolto = (
            f"✅ **SEGNALAZIONE RISOLTA**\n\n"
            f"{tipo_display}\n"
            f"📍 {zona_display}\n\n"
            "La strada è ora libera!"
        )

        # Aggiorna subito il messaggio su cui l'utente ha cliccato
        try:
            await query.edit_message_text(
                testo_risolto,
                parse_mode="Markdown"
            )
        except Exception:
            pass

        # Aggiorna anche tutti gli altri messaggi salvati per questa segnalazione
        notification_service = NotificationService(context.bot)
        await notification_service.notify_alert_resolved(alert_id, tipo, zona)

        logger.info(f"Segnalazione {alert_id} ({tipo}) risolta da {update.effective_user.id}")
    else:
        await query.answer("❌ Errore nella risoluzione", show_alert=True)


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Torna al menu principale."""
    query = update.callback_query
    await query.answer()

    welcome = (
        "🛣 **Bot Segnalazioni Strada**\n\n"
        "Segnala problemi sulla strada o controlla lo stato attuale.\n\n"
        "**Cosa vuoi fare?**"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Fai Segnalazione", callback_data="open_report_menu")],
        [InlineKeyboardButton("📊 Stato strada", callback_data="check_status")],
    ])

    await query.edit_message_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_resolve_from_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestisce la risoluzione da un messaggio di stato strada.
    Dopo la risoluzione aggiorna il messaggio con le segnalazioni rimaste
    invece di sostituirlo con 'RISOLTA', evitando di nascondere le altre segnalazioni attive.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    query = update.callback_query

    alert_id = int(query.data.replace("resolve_status_", ""))

    alert = await db.get_alert_by_id(alert_id)

    if not alert or alert["stato"] != "ATTIVO":
        await query.answer("⚠️ Segnalazione già risolta", show_alert=True)
        # Aggiorna comunque il messaggio di stato con i dati correnti
        alerts = await db.get_active_alerts()
        message = AlertService.format_status_message(alerts)
        keyboard = _build_status_keyboard(alerts)
        try:
            await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            pass
        return

    tipo = alert["tipo"]
    zona = alert.get("zona", "")

    success = await db.resolve_alert(alert_id)

    if success:
        await query.answer("🟢 Segnalazione risolta!")

        # Aggiorna il messaggio di stato con le segnalazioni rimaste
        alerts = await db.get_active_alerts()
        message = AlertService.format_status_message(alerts)
        keyboard = _build_status_keyboard(alerts)
        try:
            await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            pass

        # Aggiorna gli altri messaggi di notifica salvati
        notification_service = NotificationService(context.bot)
        await notification_service.notify_alert_resolved(alert_id, tipo, zona)

        logger.info(f"Segnalazione {alert_id} ({tipo}) risolta da stato da {update.effective_user.id}")
    else:
        await query.answer("❌ Errore nella risoluzione", show_alert=True)


def _build_status_keyboard(alerts: list[dict]) -> InlineKeyboardMarkup:
    """Tastiera per il messaggio di stato (importata qui per evitare import circolare)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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


# Handler da esportare
callback_handler = [
    CallbackQueryHandler(handle_confirm,             pattern=r"^confirm_\d+$"),
    CallbackQueryHandler(handle_resolve,             pattern=r"^resolve_\d+$"),
    CallbackQueryHandler(handle_resolve_from_status, pattern=r"^resolve_status_\d+$"),
    CallbackQueryHandler(handle_menu,                pattern=r"^menu$"),
]