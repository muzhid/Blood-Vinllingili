
import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("Error: No Token")
    exit()

url = f"https://api.telegram.org/bot{TOKEN}/deleteMyCommands"
res = requests.post(url)
print(res.json())
