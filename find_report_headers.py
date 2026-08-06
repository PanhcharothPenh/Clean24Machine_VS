import requests
import re

url = "https://sqinsights.com/assets/web-owner-portal-c3dffc22d9dfcef8a097f7ab644b8807.js"
print("Fetching Ember bundle...")
text = requests.get(url).text

# Find where LOCATION_AND_REVENUE is used
matches = re.findall(r'.{0,100}LOCATION_AND_REVENUE.{0,200}', text)
print("LOCATION_AND_REVENUE matches:")
for m in matches[:10]:
    print("MATCH:", m)
    print("-" * 50)
