"""Handler per i callback delle interazioni con segnalazioni."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
from services.alerts import AlertService
from services.notifications import NotificationService
from config import ALERT_TYPES

logger = logging.getLogger(__name__)


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la conferma di una segnalazione."""
    query = update.callback_query
    
    # Estrae l'ID della segnalazione
    alert_id = int(query.data.replace("confirm_", ""))
    
    # Conferma la segnalazione
    success = await db.confirm_alert(alert_id)
    
    if success:
        await query.answer("✅ Conferma registrata!")
        
        # Aggiorna il messaggio con i nuovi dati
        alert = await db.get_alert_by_id(alert_id)
        if alert and alert["stato"] == "ATTIVO":
            tipo_display = ALERT_TYPES.get(alert["tipo"], "⚠️")
            time_ago = AlertService.format_time_ago(alert["timestamp"])
            conferme = alert["conferme"]
            
            message = (
                f"🚨 **SEGNALAZIONE ATTIVA**\n\n"
                f"{tipo_display}\n"
                f"⏱ Aggiornato: {time_ago}\n"
                f"👥 {conferme} conferme"
            )
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Conferma", callback_data=f"confirm_{alert_id}"),
                    InlineKeyboardButton("🟢 Risolto", callback_data=f"resolve_{alert_id}")
                ]
            ])
            
            try:
                await query.edit_message_text(
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            except Exception:
                pass  # Il messaggio potrebbe essere già stato modificato
    else:
        await query.answer("⚠️ Segnalazione non più attiva", show_alert=True)


async def handle_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la risoluzione di una segnalazione."""
    query = update.callback_query
    
    # Estrae l'ID della segnalazione
    alert_id = int(query.data.replace("resolve_", ""))
    
    # Ottieni info sulla segnalazione prima di risolverla
    alert = await db.get_alert_by_id(alert_id)
    
    if not alert or alert["stato"] != "ATTIVO":
        await query.answer("⚠️ Segnalazione già risolta", show_alert=True)
        return
    
    tipo = alert["tipo"]
    
    # Risolvi la segnalazione
    success = await db.resolve_alert(alert_id)
    
    if success:
        await query.answer("🟢 Segnalazione risolta!")
        
        tipo_display = ALERT_TYPES.get(tipo, "⚠️")
        
        await query.edit_message_text(
            f"✅ **SEGNALAZIONE RISOLTA**\n\n"
            f"{tipo_display}\n\n"
            "Grazie per l'aggiornamento!",
            parse_mode="Markdown"
        )
        
        # Notifica gli altri utenti
        notification_service = NotificationService(context.bot)
        await notification_service.notify_alert_resolved(tipo)
        
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
    
    await query.edit_message_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# Handler da esportare
callback_handler = [
    CallbackQueryHandler(handle_confirm, pattern=r"^confirm_\d+$"),
    CallbackQueryHandler(handle_resolve, pattern=r"^resolve_\d+$"),
    CallbackQueryHandler(handle_menu, pattern=r"^menu$"),
]
