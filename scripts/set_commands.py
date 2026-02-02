import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

URL = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"
ADMIN_GROUP_ID = -1003695872031

# 1. Private Chat Commands (EMPTY to remove Menu)
private_commands = [] 

# 2. Admin Group Commands
group_commands = [
    {"command": "admin_access", "description": "Get Web Login"},
    {"command": "reset_password", "description": "Reset Web Password"},
    {"command": "start", "description": "Start Bot"}
]

# Function to set commands
def set_cmds(cmds, scope):
    payload = {
        "commands": cmds,
        "scope": scope
    }
    try:
        resp = requests.post(URL, json=payload)
        data = resp.json()
        if data.get("ok"):
            print(f"✅ Commands set for scope {scope.get('type')}! ({len(cmds)} cmds)")
        else:
            print(f"❌ Failed for {scope}: {data}")
    except Exception as e:
        print(f"Error: {e}")

print("Setting Scoped Commands (Removing Private Menu)...")

# Set Private (Empty List removes the menu button usually)
set_cmds(private_commands, {"type": "all_private_chats"})

# Set Admin Group (Keep commands)
set_cmds(group_commands, {"type": "chat", "chat_id": str(ADMIN_GROUP_ID)})

# Also clear Default just in case
set_cmds([], {"type": "default"})

print("Done.")
