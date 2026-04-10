"""Servizio per la gestione delle segnalazioni."""

from datetime import datetime
from config import ALERT_TYPES


class AlertService:
    """Utility per formattazione e gestione segnalazioni."""
    
    @staticmethod
    def format_time_ago(timestamp_str: str) -> str:
        """Converte un timestamp in formato 'X minuti fa'."""
        try:
            # Parse del timestamp dal database
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = timestamp_str
            
            now = datetime.utcnow()
            diff = now - timestamp.replace(tzinfo=None)
            
            minutes = int(diff.total_seconds() / 60)
            
            if minutes < 1:
                return "adesso"
            elif minutes == 1:
                return "1 minuto fa"
            elif minutes < 60:
                return f"{minutes} minuti fa"
            else:
                hours = minutes // 60
                if hours == 1:
                    return "1 ora fa"
                return f"{hours} ore fa"
                
        except Exception:
            return "tempo sconosciuto"
    
    @staticmethod
    def get_alert_emoji(tipo: str) -> str:
        """Restituisce l'emoji per un tipo di segnalazione."""
        return ALERT_TYPES.get(tipo, "⚠️ Sconosciuto")
    
    @staticmethod
    def format_alert_message(alert: dict) -> str:
        """Formatta una segnalazione per la visualizzazione."""
        tipo_display = AlertService.get_alert_emoji(alert["tipo"])
        time_ago = AlertService.format_time_ago(alert["timestamp"])
        conferme = alert["conferme"]
        
        conferme_text = "1 conferma" if conferme == 1 else f"{conferme} conferme"
        
        return f"{tipo_display}\n⏱ {time_ago} • 👥 {conferme_text}"
    
    @staticmethod
    def format_status_message(alerts: list[dict]) -> str:
        """Formatta il messaggio di stato della strada."""
        if not alerts:
            return "🟢 **Strada libera**\n\nNessuna segnalazione attiva."
        
        message_parts = ["🔴 **Attenzione: segnalazioni attive**\n"]
        
        for alert in alerts:
            message_parts.append(AlertService.format_alert_message(alert))
            message_parts.append("")  # Riga vuota tra segnalazioni
        
        return "\n".join(message_parts)
