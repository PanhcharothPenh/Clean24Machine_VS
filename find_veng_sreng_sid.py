import requests
import json

base_url = "https://vxpjcrk7iorjzymtfpuy5csrzm0rwugg.lambda-url.us-east-1.on.aws/?sid="

# Let's test if there are other SIDs or search
test_sids = [1517969, 1517968, 1517970, 1517960, 1517965, 1517975, 1517900, 1517950, 1518000]

for sid in range(1517960, 1517980):
    try:
        r = requests.get(f"{base_url}{sid}", timeout=5)
        if r.status_code == 200:
            d = r.json()
            room_name = d.get("room", {}).get("room_name", "")
            machine_count = len(d.get("machines", {}))
            print(f"SID: {sid} | Room Name: '{room_name}' | Machine Count: {machine_count}")
    except Exception:
        pass
