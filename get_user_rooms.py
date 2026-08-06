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

endpoints = [
    "https://api.sqinsights.com/organizations/4781102",
    "https://api.sqinsights.com/organizations/4781102/rooms",
    "https://api.sqinsights.com/rooms?filter%5Borganization%5D=4781102",
    "https://api.sqinsights.com/users/cdaa3761-eccf-42ae-bf16-cf838597d844?include=organizations,rooms",
    "https://api.sqinsights.com/locations?filter%5Borganization%5D=4781102"
]

for ep in endpoints:
    try:
        res = requests.get(ep, headers=auth_headers, timeout=10)
        print(f"URL: {ep} -> Status: {res.status_code}")
        if res.status_code == 200:
            print("Response:", res.text[:500])
            print()
    except Exception as e:
        print(f"Error {ep}: {e}")
