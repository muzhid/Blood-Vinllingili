import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID")
    exit(1)

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def delete_message(msg_id):
    url = f"{BASE_URL}/deleteMessage"
    data = {"chat_id": CHANNEL_ID, "message_id": msg_id}
    try:
        res = requests.post(url, json=data)
        return res.json()
    except Exception as e:
        print(f"Error deleting {msg_id}: {e}")
        return {"ok": False}

def clear_channel():
    print(f"Clearing Channel {CHANNEL_ID}...")
    
    # 1. Send dummy message to get latest ID
    send_url = f"{BASE_URL}/sendMessage"
    res = requests.post(send_url, json={"chat_id": CHANNEL_ID, "text": "Cleaning up... 🧹"})
    if not res.ok:
        print(f"Failed to access channel: {res.text}")
        return

    latest_id = res.json()["result"]["message_id"]
    print(f"Latest Message ID: {latest_id}")
    
    # 2. Iterate downwards
    # Limit to last 200 messages to be safe/fast. Increase if needed.
    count = 0
    for i in range(latest_id, latest_id - 200, -1):
        r = delete_message(i)
        if r.get("ok"):
            print(f"Deleted {i}")
            count += 1
        else:
            # print(f"Skipped {i} (Not found or too old)")
            pass
        time.sleep(0.05) # Avoid rate limits

    print(f"Finished. Deleted {count} messages.")

if __name__ == "__main__":
    clear_channel()
