import asyncio
import os
from api.index import process_update
from dotenv import load_dotenv
import requests

load_dotenv()

async def main():
    offset = 0
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("Bot token missing!")
        return
    
    # Clear webhook first (cannot poll if webhook is active)
    print("Clearing webhook...")
    try:
        requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
    except Exception as e:
        print(f"Error clearing webhook: {e}")
    
    print("✅ Bot polling started... (Press Ctrl+C to stop)")
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=10"
            resp = requests.get(url, timeout=40).json()
            if "result" in resp:
                for update in resp["result"]:
                    offset = update["update_id"] + 1
                    print(f"Processing update: {update['update_id']}")
                    await process_update(update)
            elif "ok" in resp and not resp["ok"]:
                print(f"Telegram Error: {resp}")
                
        except Exception as e:
            print(f"Polling Error: {e}")
            await asyncio.sleep(2)
        
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
