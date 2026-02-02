import requests
import os

token = "8226446742:AAFe-8deuzQnP4NZFiOnVedZ2Kd1LnXlJJk"
url = "https://naifaru-blood-donors.vercel.app/api/webhook"

print(f"Setting webhook to: {url}")
try:
    resp = requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={url}")
    print(resp.json())
except Exception as e:
    print(f"Error: {e}")
