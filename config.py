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
    "posto_blocco": "🚔 Posto di blocco",
    "macchina_ferma": "🚘 Macchina ferma",
    "strada_allagata": "🌊 Strada allagata",
    "lavori": "🦺 Lavori in corso",
    "ghiaccio": "🧊 Ghiaccio",
    "nebbia": "🌫️ Nebbia",
}

# Zone disponibili per le segnalazioni
ALERT_ZONES = {
    "fermata_bus_segni": "🚏 Fermata bus Segni",
    "curva_ceci": "↩️ Curva a Ceci",
    "meta_strada": "📍 Metà strada",
    "chiesetta": "⛪ Chiesetta",
    "piroland": "🎡 Piroland",
    "cava": "⛏️ Cava",
    "semaforo_murillo": "🚦 Semaforo Murillo",
}

# Validazione
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN non configurato nel file .env")
