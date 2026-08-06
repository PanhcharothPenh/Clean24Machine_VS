import requests
import json
from datetime import datetime
from config import Config

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-api-key": "4da79517795f579f1717d55b25fb1e9d",
    "Content-Type": "application/json",
    "Origin": "https://sqinsights.com",
    "Referer": "https://sqinsights.com/"
}

# 1. Login
r = requests.post("https://api.sqinsights.com/auth/login", headers=headers, json={"email": Config.SQ_EMAIL, "password": Config.SQ_PASSWORD})
data = r.json()
token = data.get("meta", {}).get("authToken")
user_id = data.get("data", {}).get("id")

print("Auth Token:", token[:20] if token else None)

auth_headers = dict(headers)
auth_headers["alliancels-auth-token"] = token
auth_headers["Authorization"] = f"Bearer {token}"

today_str = datetime.now().strftime("%Y-%m-%d")
today_mdy = datetime.now().strftime("%m/%d/%Y")

# Test queries for overview KPIs
test_endpoints = [
    f"https://api.sqinsights.com/reports/LOCATION_AND_REVENUE/kpi?filter%5BstartDate%5D={today_str}&filter%5BendDate%5D={today_str}",
    f"https://api.sqinsights.com/reports/LOCATION_AND_REVENUE/kpi?startDate={today_str}&endDate={today_str}",
    f"https://api.sqinsights.com/reports/LOCATION_AND_REVENUE/kpi?filter%5BorganizationId%5D=4781102&filter%5BstartDate%5D={today_str}&filter%5BendDate%5D={today_str}",
    f"https://api.sqinsights.com/reports/LOCATION_AND_REVENUE/kpi?filter%5BroomId%5D=23546&filter%5BstartDate%5D={today_str}&filter%5BendDate%5D={today_str}",
    f"https://api.sqinsights.com/reports/STORE_OVERVIEW?filter%5BstartDate%5D={today_str}&filter%5BendDate%5D={today_str}",
    f"https://api.sqinsights.com/reports/DAILY_OVERVIEW?filter%5BstartDate%5D={today_str}&filter%5BendDate%5D={today_str}",
    f"https://platform.sqinsights.com/api/v1/reports/LOCATION_AND_REVENUE/kpi?startDate={today_str}&endDate={today_str}"
]

for ep in test_endpoints:
    try:
        res = requests.get(ep, headers=auth_headers, timeout=10)
        print(f"URL: {ep} -> Status: {res.status_code}")
        if res.status_code == 200:
            print("FOUND REVENUE KPI DATA!")
            print(json.dumps(res.json(), indent=2)[:1000])
            print("=" * 60)
        else:
            print("Response:", res.text[:250])
    except Exception as e:
        print(f"Error {ep}: {e}")
