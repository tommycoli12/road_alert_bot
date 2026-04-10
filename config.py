"""Configurazione centralizzata del bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# Token del bot Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Durata segnalazioni in minuti
ALERT_EXPIRY_MINUTES = int(os.getenv("ALERT_EXPIRY_MINUTES", 60))

# Percorso database
DATABASE_PATH = os.getenv("DATABASE_PATH", "road_alerts.db")

# Tipi di segnalazione disponibili
ALERT_TYPES = {
    "incidente": "🚗 Incidente",
    "animale": "🐗 Animale",
    "frana": "⛰️ Frana",
    "altro": "⚠️ Altro"
}

# Validazione
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN non configurato nel file .env")
