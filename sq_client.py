import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Custom mapping for Clean24 Veng Sreng (Room 23546)
MACHINE_METADATA = {
    "1517964": {"name": "W1", "capacity": "9kg", "type": "Washer Extractor 9 kg"},
    "1517965": {"name": "W2", "capacity": "14kg", "type": "Washer Extractor 14 kg"},
    "1517966": {"name": "W3", "capacity": "14kg", "type": "Washer Extractor 14 kg"},
    "1517967": {"name": "W4", "capacity": "14kg", "type": "Washer Extractor 14 kg"},
    "1517968": {"name": "W5", "capacity": "14kg", "type": "Washer Extractor 14 kg"},
    "1517969": {"name": "W6", "capacity": "18kg", "type": "Washer Extractor 18 kg"},
    "1517970": {"name": "D7", "capacity": "14kg", "type": "Tumbler 14 kg Stack"},
    "1517971": {"name": "D8", "capacity": "14kg", "type": "Tumbler 14 kg Stack"},
    "1517972": {"name": "D9", "capacity": "14kg", "type": "Tumbler 14 kg Stack"},
    "1517973": {"name": "D10", "capacity": "14kg", "type": "Tumbler 14 kg Stack"},
}

class SpeedQueenClient:
    """
    Client for interacting with Speed Queen Insights API and real-time status & revenue services.
    """

    API_BASE = "https://api.sqinsights.com"
    LAMBDA_STATUS_URL = "https://vxpjcrk7iorjzymtfpuy5csrzm0rwugg.lambda-url.us-east-1.on.aws"
    DEFAULT_API_KEY = "4da79517795f579f1717d55b25fb1e9d"

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.auth_token: Optional[str] = None
        self.organization_id: str = "4781102"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "x-api-key": self.DEFAULT_API_KEY,
            "Content-Type": "application/json",
            "Origin": "https://sqinsights.com",
            "Referer": "https://sqinsights.com/"
        })

    def login(self) -> bool:
        if not self.email or not self.password or self.email == "your_email@example.com":
            logger.warning("No valid Speed Queen credentials supplied.")
            return False

        url = f"{self.API_BASE}/auth/login"
        payload = {
            "email": self.email,
            "password": self.password
        }

        try:
            res = self.session.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                token = data.get("meta", {}).get("authToken") or data.get("token")
                user_rel = data.get("data", {}).get("relationships", {}).get("organization", {}).get("data", {})
                if user_rel.get("id"):
                    self.organization_id = str(user_rel["id"])

                if token:
                    self.auth_token = token
                    self.session.headers.update({
                        "alliancels-auth-token": token,
                        "Authorization": f"Bearer {token}"
                    })
                    logger.info("Successfully authenticated with Speed Queen Insights.")
                    return True
        except Exception as e:
            logger.error(f"Error connecting to Speed Queen login API: {e}")

        return False

    def get_location_and_machines(self, sid: str, room_id: Optional[str] = "23546") -> Dict[str, Any]:
        if room_id:
            url = f"{self.LAMBDA_STATUS_URL}/?sid={sid}&roomId={room_id}"
        else:
            url = f"{self.LAMBDA_STATUS_URL}/?sid={sid}"

        try:
            res = self.session.get(url, timeout=12)
            if res.status_code == 200:
                data = res.json()
                room_info = data.get("room", {})
                all_machines = data.get("machines", {})

                if room_id:
                    filtered_machines = {k: v for k, v in all_machines.items() if str(v.get("roomId")) == str(room_id)}
                else:
                    filtered_machines = all_machines

                return {
                    "sid": sid,
                    "room_id": room_id,
                    "location_name": room_info.get("room_name", "Clean24 Veng Sreng"),
                    "total_machines": len(filtered_machines),
                    "machines": filtered_machines,
                    "raw_data": data,
                    "error": False
                }
        except Exception as e:
            logger.error(f"Error fetching machine data for SID {sid} Room {room_id}: {e}")

        return {
            "sid": sid,
            "room_id": room_id,
            "location_name": "Clean24 Veng Sreng",
            "total_machines": 0,
            "machines": {},
            "error": True
        }

    def get_machine_summary(self, sid: str, room_id: Optional[str] = "23546") -> Dict[str, Any]:
        loc_data = self.get_location_and_machines(sid, room_id=room_id)
        if loc_data.get("error"):
            return {
                "sid": sid,
                "location_name": "Clean24 Veng Sreng",
                "status": "ERROR",
                "summary_text": "Unable to fetch machine status from Speed Queen API.",
                "counts": {},
                "error": True
            }

        machines = loc_data.get("machines", {})
        counts = {
            "AVAILABLE": 0,
            "RUNNING": 0,
            "OUT_OF_SERVICE": 0
        }

        avail_lines = []
        running_lines = []
        oos_lines = []

        sorted_machine_ids = sorted(machines.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))

        for m_id in sorted_machine_ids:
            m_info = machines[m_id]
            meta = MACHINE_METADATA.get(m_id, {"name": f"W{m_id}", "capacity": "14kg", "type": "Washer/Dryer"})
            m_name = meta["name"]
            m_cap = meta["capacity"]

            status_raw = str(m_info.get("statusId", "OTHER")).upper()
            rem_sec = m_info.get("remainingSeconds", 0)
            rem_min = (rem_sec // 60) if (rem_sec and rem_sec < 1800) else 0

            if status_raw in ["IN_USE", "RUNNING", "WASHING", "DRYING"]:
                counts["RUNNING"] += 1
                time_str = f"⏱️ {rem_min} នាទី" if rem_min > 0 else "⏱️ កំពុងដំណើរការ"
                running_lines.append(f"• {m_name} – {time_str}")
            elif status_raw in ["ERROR", "UNAVAILABLE", "OUT_OF_SERVICE", "FAULT"]:
                counts["OUT_OF_SERVICE"] += 1
                oos_lines.append(f"• {m_name} ({m_cap})")
            else:
                counts["AVAILABLE"] += 1
                avail_lines.append(f"• {m_name} ({m_cap})")

        return {
            "sid": sid,
            "location_name": loc_data.get("location_name", "Clean24 Veng Sreng"),
            "total_count": loc_data.get("total_machines"),
            "counts": counts,
            "avail_lines": avail_lines,
            "running_lines": running_lines,
            "oos_lines": oos_lines,
            "error": False
        }

    def get_live_daily_revenue_report(self, room_id: str = "23546", target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches REAL-TIME live daily revenue directly from Speed Queen Insights LOCATION_AND_REVENUE report API.
        """
        if not self.auth_token:
            self.login()

        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        url = f"{self.API_BASE}/reports/LOCATION_AND_REVENUE?organizationId={self.organization_id}&roomId={room_id}&startDate={date_str}&endDate={date_str}"

        try:
            res = self.session.get(url, timeout=12)
            if res.status_code == 401:
                if self.login():
                    res = self.session.get(url, timeout=12)

            if res.status_code == 200:
                data = res.json()
                attrs = data.get("data", {}).get("attributes", {})
                overview_list = attrs.get("overview", [])

                total_rev = 0
                total_turns = 0
                washers_rev = 0
                washers_turns = 0
                dryers_rev = 0
                dryers_turns = 0

                for item in overview_list:
                    item_id = item.get("id")
                    if item_id == "Totals":
                        total_rev = item.get("revenue", 0)
                        total_turns = item.get("turns", 0)
                    elif item_id == "Washers":
                        washers_rev = item.get("revenue", 0)
                        washers_turns = item.get("turns", 0)
                    elif item_id == "Dryers":
                        dryers_rev = item.get("revenue", 0)
                        dryers_turns = item.get("turns", 0)

                return {
                    "date": date_str,
                    "location_name": "Clean24 Veng Sreng",
                    "total_revenue": total_rev,
                    "total_turns": total_turns,
                    "washers_revenue": washers_rev,
                    "washers_turns": washers_turns,
                    "dryers_revenue": dryers_rev,
                    "dryers_turns": dryers_turns,
                    "error": False
                }
            else:
                logger.error(f"Revenue API returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Error fetching live revenue report: {e}")

        return {
            "date": date_str,
            "location_name": "Clean24 Veng Sreng",
            "total_revenue": 0,
            "total_turns": 0,
            "error": True
        }
