"""Servizio per l'invio di notifiche agli utenti."""

import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import database as db
from config import ALERT_TYPES

logger = logging.getLogger(__name__)


class NotificationService:
    """Gestisce l'invio di notifiche broadcast."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def notify_new_alert(self, alert_id: int, tipo: str, exclude_user: int = None) -> int:
        """
        Notifica tutti gli utenti di una nuova segnalazione.
        Ritorna il numero di utenti notificati con successo.
        """
        users = await db.get_subscribed_users()
        tipo_display = ALERT_TYPES.get(tipo, "⚠️ Sconosciuto")
        
        message = f"🚨 **NUOVA SEGNALAZIONE**\n\n{tipo_display}\n\nFai attenzione!"
        
        # Bottoni per interagire
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Conferma", callback_data=f"confirm_{alert_id}"),
                InlineKeyboardButton("🟢 Risolto", callback_data=f"resolve_{alert_id}")
            ]
        ])
        
        success_count = 0
        
        for user_id in users:
            # Salta l'utente che ha creato la segnalazione
            if user_id == exclude_user:
                continue
                
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                success_count += 1
            except TelegramError as e:
                logger.warning(f"Impossibile notificare utente {user_id}: {e}")
        
        logger.info(f"Notifica inviata a {success_count}/{len(users)} utenti")
        return success_count
    
    async def notify_alert_resolved(self, tipo: str) -> int:
        """
        Notifica tutti gli utenti che una segnalazione è stata risolta.
        Ritorna il numero di utenti notificati con successo.
        """
        users = await db.get_subscribed_users()
        tipo_display = ALERT_TYPES.get(tipo, "⚠️ Sconosciuto")
        
        message = f"✅ **SEGNALAZIONE RISOLTA**\n\n{tipo_display}\n\nLa strada è ora libera!"
        
        success_count = 0
        
        for user_id in users:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown"
                )
                success_count += 1
            except TelegramError as e:
                logger.warning(f"Impossibile notificare utente {user_id}: {e}")
        
        return success_count
