import requests
import json
from config import Config

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-api-key": "4da79517795f579f1717d55b25fb1e9d",
    "Content-Type": "application/json",
    "Origin": "https://sqinsights.com",
    "Referer": "https://sqinsights.com/"
}

r = requests.post("https://api.sqinsights.com/auth/login", headers=headers, json={"email": Config.SQ_EMAIL, "password": Config.SQ_PASSWORD})
data = r.json()
token = data.get("meta", {}).get("authToken")

auth_headers = dict(headers)
auth_headers["alliancels-auth-token"] = token
auth_headers["Authorization"] = f"Bearer {token}"

# Fetch locations/rooms via platform API or sqinsights endpoints
urls = [
    "https://api.sqinsights.com/rooms?filter%5BorganizationId%5D=4781102",
    "https://api.sqinsights.com/locations?filter%5BorganizationId%5D=4781102",
    "https://api.sqinsights.com/v1/rooms",
    "https://platform.sqinsights.com/api/v1/rooms",
    "https://platform.sqinsights.com/api/v1/locations"
]

for url in urls:
    try:
        res = requests.get(url, headers=auth_headers, timeout=10)
        print(f"URL: {url} -> Status: {res.status_code}")
        if res.status_code == 200:
            print("Response:", res.text[:600])
            print()
    except Exception as e:
        print(f"Error {url}: {e}")
