import requests
import json

url = "https://vxpjcrk7iorjzymtfpuy5csrzm0rwugg.lambda-url.us-east-1.on.aws/?sid=1517969"
res = requests.get(url)
data = res.json()

machines = data.get("machines", {})
print(f"Total machines: {len(machines)}")

target_sns = [
    "2601600217", "2601601650", "2505600767", "2505600764", 
    "2505600766", "2506602223", "2601600863", "2507601838"
]

matched = []
for m_id, m_info in machines.items():
    control_id = str(m_info.get("controlId", ""))
    # Convert raw JSON string to text search
    m_str = json.dumps(m_info)
    for sn in target_sns:
        if sn in m_str:
            matched.append((m_id, sn))

print("Matched machine IDs with serial numbers:")
print(matched)
