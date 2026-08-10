import json
import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Set
from config import Config

logger = logging.getLogger(__name__)

class KVRedisClient:
    """
    Minimalist REST/HTTP client for Vercel KV / Upstash Redis to work in serverless environments
    without heavy standard client library dependencies.
    """
    def __init__(self):
        self.url = os.getenv("KV_REST_API_URL", "").rstrip("/")
        self.token = os.getenv("KV_REST_API_TOKEN", "")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.enabled = bool(self.url and self.token)

    def execute(self, cmd_list: List[Any]) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            res = requests.post(self.url, json=cmd_list, headers=self.headers, timeout=10)
            if res.status_code == 200:
                return res.json().get("result")
            else:
                logger.error(f"Vercel KV API Error {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Vercel KV Connection Exception: {e}")
        return None

class StateTracker:
    """
    Manages persistent machine state tracking and subscriber chat persistence.
    Supports local JSON files or Vercel KV / Upstash Redis database.
    """

    def __init__(self, db_path: str = "machine_states.json", chats_path: str = "subscribed_chats.json"):
        self.db_path = Path(db_path)
        self.chats_path = Path(chats_path)
        self.kv = KVRedisClient()

        if self.kv.enabled:
            logger.info("Vercel KV (Upstash Redis) detected. Using cloud persistence layer.")
            self.states = self._load_states_kv()
            self.daily_revenue = self._load_revenue_kv()
            self.subscribed_chats = self._load_chats_kv()
        else:
            logger.info("Vercel KV not configured. Using local JSON files.")
            self.data = self._load_states_local()
            self.states = self.data.get("states", {})
            self.daily_revenue = self.data.get("daily_revenue", {})
            self.subscribed_chats = self._load_chats_local()

        # Always ensure default configured chat IDs are added
        for cid in Config.DEFAULT_CHAT_IDS:
            self.subscribed_chats.add(cid)
        self.save_chats()

    # --- Local File Persistence ---
    def _load_states_local(self) -> Dict[str, Any]:
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

    def _load_chats_local(self) -> Set[str]:
        if self.chats_path.exists():
            try:
                with open(self.chats_path, "r", encoding="utf-8") as f:
                    chats = json.load(f)
                    return set(chats)
            except Exception as e:
                logger.error(f"Error loading chats DB {self.chats_path}: {e}")
        return set(Config.DEFAULT_CHAT_IDS)

    def _save_states_local(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({
                    "states": self.states,
                    "daily_revenue": self.daily_revenue
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state DB {self.db_path}: {e}")

    def _save_chats_local(self):
        try:
            with open(self.chats_path, "w", encoding="utf-8") as f:
                json.dump(list(self.subscribed_chats), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving chats DB {self.chats_path}: {e}")

    # --- Vercel KV Persistence ---
    def _load_states_kv(self) -> Dict[str, Any]:
        val = self.kv.execute(["GET", "clean24:states"])
        if val:
            try:
                return json.loads(val)
            except Exception as e:
                logger.error(f"Error decoding KV states: {e}")
        return {}

    def _load_revenue_kv(self) -> Dict[str, Any]:
        val = self.kv.execute(["GET", "clean24:daily_revenue"])
        if val:
            try:
                return json.loads(val)
            except Exception as e:
                logger.error(f"Error decoding KV revenue: {e}")
        return {}

    def _load_chats_kv(self) -> Set[str]:
        val = self.kv.execute(["GET", "clean24:subscribed_chats"])
        if val:
            try:
                return set(json.loads(val))
            except Exception as e:
                logger.error(f"Error decoding KV chats: {e}")
        return set(Config.DEFAULT_CHAT_IDS)

    def _save_states_kv(self):
        self.kv.execute(["SET", "clean24:states", json.dumps(self.states)])
        self.kv.execute(["SET", "clean24:daily_revenue", json.dumps(self.daily_revenue)])

    def _save_chats_kv(self):
        self.kv.execute(["SET", "clean24:subscribed_chats", json.dumps(list(self.subscribed_chats))])

    # --- Unified API ---
    def save_chats(self):
        if self.kv.enabled:
            self._save_chats_kv()
        else:
            self._save_chats_local()

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

        if self.kv.enabled:
            self._save_states_kv()
        else:
            self._save_states_local()

        return has_changed, old_data, new_status_data
