import os
from dotenv import load_dotenv

load_dotenv()

def sanitize_env_var(val: str) -> str:
    if not val:
        return ""
    val = val.strip()
    if val.startswith("="):
        val = val[1:].strip()
    return val

class Config:
    TELEGRAM_BOT_TOKEN = sanitize_env_var(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    TELEGRAM_CHAT_ID = sanitize_env_var(os.getenv("TELEGRAM_CHAT_ID", ""))
    
    SQ_EMAIL = sanitize_env_var(os.getenv("SQ_EMAIL", ""))
    SQ_PASSWORD = sanitize_env_var(os.getenv("SQ_PASSWORD", ""))
    
    CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
    
    # Machine SIDs to track
    TRACKED_SIDS_RAW = sanitize_env_var(os.getenv("TRACKED_MACHINE_SIDS", "1517969"))
    TRACKED_MACHINE_SIDS = [s.strip() for s in TRACKED_SIDS_RAW.split(",") if s.strip()]
