import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Set
from config import Config

logger = logging.getLogger(__name__)

class StateTracker:
    """
    Manages persistent machine state tracking and subscriber chat persistence.
    """

    def __init__(self, db_path: str = "machine_states.json", chats_path: str = "subscribed_chats.json"):
        self.db_path = Path(db_path)
        self.chats_path = Path(chats_path)
        self.data: Dict[str, Any] = self._load_states()
        self.states: Dict[str, Dict[str, Any]] = self.data.get("states", {})
        self.daily_revenue: Dict[str, Any] = self.data.get("daily_revenue", {})
        self.subscribed_chats: Set[str] = self._load_chats()

        # Always ensure default configured chat IDs are added
        for cid in Config.DEFAULT_CHAT_IDS:
            self.subscribed_chats.add(cid)
        self.save_chats()

    def _load_states(self) -> Dict[str, Any]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if "states" not in content:
                        return {"states": content, "daily_revenue": {}}
                    return content
            except Exception as e:
                logger.error(f"Error loading state DB {self.db_path}: {e}")
        return {"states": {}, "daily_revenue": {}}

    def _save_states(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({
                    "states": self.states,
                    "daily_revenue": self.daily_revenue
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state DB {self.db_path}: {e}")

    def _load_chats(self) -> Set[str]:
        if self.chats_path.exists():
            try:
                with open(self.chats_path, "r", encoding="utf-8") as f:
                    chats = json.load(f)
                    return set(chats)
            except Exception as e:
                logger.error(f"Error loading chats DB {self.chats_path}: {e}")
        return set(Config.DEFAULT_CHAT_IDS)

    def save_chats(self):
        try:
            with open(self.chats_path, "w", encoding="utf-8") as f:
                json.dump(list(self.subscribed_chats), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving chats DB {self.chats_path}: {e}")

    def add_subscriber(self, chat_id: str):
        self.subscribed_chats.add(str(chat_id))
        self.save_chats()

    def remove_subscriber(self, chat_id: str):
        self.subscribed_chats.discard(str(chat_id))
        self.save_chats()

    def update_machine_state(self, sid: str, new_status_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Dict[str, Any]]:
        new_status = new_status_data.get("status", "UNKNOWN")
        if new_status in ["AUTH_REQUIRED", "UNKNOWN"]:
            return False, None, new_status_data

        old_data = self.states.get(sid)
        old_status = old_data.get("status") if old_data else None

        has_changed = (old_status is not None) and (old_status != new_status)

        self.states[sid] = new_status_data
        self._save_states()

        return has_changed, old_data, new_status_data
