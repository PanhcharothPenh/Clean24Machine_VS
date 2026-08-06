import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the current directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    SQ_EMAIL = os.getenv("SQ_EMAIL", "").strip()
    SQ_PASSWORD = os.getenv("SQ_PASSWORD", "").strip()
    
    # Machine SIDs as list of strings
    _sids_raw = os.getenv("TRACKED_MACHINE_SIDS", "1517969")
    TRACKED_MACHINE_SIDS = [sid.strip() for sid in _sids_raw.split(",") if sid.strip()]
    
    try:
        CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
    except ValueError:
        CHECK_INTERVAL_SECONDS = 60

    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.SQ_EMAIL or cls.SQ_EMAIL == "your_email@example.com":
            missing.append("SQ_EMAIL")
        if not cls.SQ_PASSWORD or cls.SQ_PASSWORD == "your_password_here":
            missing.append("SQ_PASSWORD")
        return missing
