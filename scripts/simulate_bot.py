import os
import sys
import json
import requests
import time
import random

# Set MOCK env var so utils.py prints instead of sending
os.environ["MOCK_TELEGRAM"] = "true"

SERVER_URL = "http://127.0.0.1:8000/api/webhook"
ADMIN_GROUP_ID = -1003695872031 # Matches default in api/index.py

def main():
    print("-------------------------------------------------")
    print("🩸 Blood Donation Bot - Offline Simulator v2.0 🩸")
    print("-------------------------------------------------")
    print("Commands:")
    print("  /role user   -> Switch to Private Chat (Default)")
    print("  /role admin  -> Switch to Admin Group Chat")
    print("  callback:XYZ -> Simulate clicking a button with data 'XYZ'")
    print("  /exit        -> Quit")
    print("-------------------------------------------------")

    # Default State
    current_role = "user"
    user_id = 999999
    first_name = "SimUser"
    chat_id = user_id
    chat_type = "private"

    while True:
        prompt_label = f"\n[{current_role.upper()} ({chat_id})]: "
        text = input(prompt_label).strip()
        
        if not text:
            continue

        if text == "/exit":
            break
        
        # --- COMMANDS ---
        if text.startswith("/role"):
            parts = text.split()
            if len(parts) > 1:
                role = parts[1].lower()
                if role == "admin":
                    current_role = "admin"
                    chat_id = ADMIN_GROUP_ID
                    chat_type = "supergroup"
                    print(f">> Switched to ADMIN GROUP ({chat_id})")
                else:
                    current_role = "user"
                    chat_id = user_id
                    chat_type = "private"
                    print(f">> Switched to PRIVATE CHAT ({chat_id})")
            continue

        # --- PAYLOAD CONSTRUCTION ---
        timestamp = int(time.time())
        update = {
            "update_id": timestamp,
        }

        # Handle Callbacks (Buttons)
        if text.startswith("callback:"):
            data_payload = text.split(":", 1)[1].strip()
            update["callback_query"] = {
                "id": str(timestamp),
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "language_code": "en"
                },
                "message": {
                    "message_id": timestamp,
                    "chat": {
                        "id": chat_id,
                        "type": chat_type
                    },
                    "date": timestamp,
                    "text": "[Button Message]"
                },
                "data": data_payload
            }
            print(f">> Sending CALLBACK: {data_payload}")

        # Handle Normal Messages (Text)
        else:
            update["message"] = {
                "message_id": timestamp,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "language_code": "en"
                },
                "chat": {
                    "id": chat_id,
                    "type": chat_type
                },
                "date": timestamp,
                "text": text
            }
            # Admin Group Logic often checks for Reply headers, Photos etc.
            # This sim only creates text.
            # To simulate 'Reply to Scan', we need 'reply_to_message' structure.
            # Simple syntax hack: "reply:REF:123|message"
            if text.startswith("reply:"):
                # Format: reply:REF-TEXT|ACTUAL-TEXT
                # Example: reply:REF:123|9999999
                try:
                    meta, actual_text = text.split("|", 1)
                    reply_text = meta.split(":", 1)[1] # remove 'reply:'
                    
                    update["message"]["text"] = actual_text
                    update["message"]["reply_to_message"] = {
                        "message_id": timestamp - 10,
                        "from": {"id": 888888, "first_name": "Bot"},
                        "chat": {"id": chat_id},
                        "text": reply_text
                    }
                    print(f">> Simulate REPLYING to message: '{reply_text}'")
                except:
                    print("Error parsing reply syntax. Use: reply:TargetText|MyMessage")

        # --- SEND ---
        try:
            res = requests.post(SERVER_URL, json=update)
            if res.status_code != 200:
                print(f"[Error] Server returned {res.status_code}: {res.text}")
            else:
                print(">> Sent. Watch Backend Terminal for reply.")
                
        except requests.exceptions.ConnectionError:
            print("[Error] Could not connect to server. Is it running on port 8000?")

if __name__ == "__main__":
    main()
