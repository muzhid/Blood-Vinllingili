import os
import sys
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load env vars
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Supabase credentials missing (SUPABASE_URL, SUPABASE_KEY).")
    sys.exit(1)

supabase = create_client(url, key)

raw_data = """
# PASTE YOUR DATA HERE
# Format: BloodType Name Phone
# Example:
# A+ John Doe 1234567
"""

def parse_line(line):
    line = line.strip()
    if not line: return None
    
    # helper: normalize blood type
    def norm_bt(bt):
        bt = bt.upper().replace(" ", "").replace("(NEGATIVE)", "-")
        return bt

    # Regex breakdown:
    # 1. Start with Blood type: (A|B|AB|O) then optional space then (+|-) then optional (Negative)
    # 2. Then Name (lazy match)
    # 3. Then optional separator like - or spaces
    # 4. Then Phone (digits)
    # 5. End
    
    # We do a somewhat loose match to catch variations like "O + Ulwaan" or "O-(Negative)"
    
    # Try splitting by first occurrence of digits at the end
    phone_match = re.search(r'(\d{7,})\.?$', line)
    if not phone_match:
        print(f"⚠️ Skipping (No Phone): {line}")
        return None
    
    phone = phone_match.group(1)
    
    # Remainder is Blood + Name
    # Remove phone from line for easier parsing
    remainder = line[:phone_match.start()].strip()
    
    # Remove trailing dash/dot
    if remainder.endswith("-") or remainder.endswith("."):
        remainder = remainder[:-1].strip()

    # Extract Blood Type at start
    # Matches: A+, B-, AB+, O+, O + (with space), O-(Negative)
    bt_match = re.match(r'^([ABO]{1,2})\s*([+-])(?:\(Negative\))?', remainder, re.IGNORECASE)
    
    if not bt_match:
        print(f"⚠️ Skipping (No Blood Type): {line}")
        return None
        
    blood_raw = bt_match.group(0)
    blood_display = bt_match.group(1) + bt_match.group(2) # e.g. A + -> A+
    
    name = remainder[len(blood_raw):].strip()
    # Cleanup name (remove leading hyphens if space was missing)
    if name.startswith("-"): name = name[1:].strip()
    
    return {
        "full_name": name,
        "blood_type": blood_display.upper().strip(),
        "phone_number": phone
    }

parsed_users = []
lines = raw_data.strip().split('\n')
for l in lines:
    u = parse_line(l)
    if u:
        parsed_users.append(u)

print(f"Parsed {len(parsed_users)} users.")

# Insert
count = 0
for u in parsed_users:
    # Generate a fake telegram_id. 
    # Use negative or very large number. 
    # Since these are real users we want them to stay.
    # We can use the phone number as a seed for a fake ID to keep it consistent if re-run?
    # Or just random.
    # Let's use 2000000000 + phone (approx) to be safe from real TG IDs?
    # Real TG IDs are ~10 digits, e.g. 123456789. Max int is large.
    # Let's use 99 + phone (which is 7 digits) -> 997654321.
    fake_id = int("99" + u["phone_number"])
    
    data = {
        "telegram_id": fake_id,
        "full_name": u["full_name"],
        "blood_type": u["blood_type"],
        "phone_number": u["phone_number"],
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    
    try:
        # Upsert based on phone number? 
        # Schema might rely on telegram_id as PK.
        # Let's try inserting, on conflict (telegram_id) do update?
        # But we don't know if this ID existed.
        # Let's check phone first.
        existing = supabase.table("users").select("*").eq("phone_number", u["phone_number"]).execute()
        if existing.data:
            print(f"Skipping {u['full_name']} (Phone {u['phone_number']} exists)")
            continue
            
        supabase.table("users").insert(data).execute()
        print(f"Inserted: {u['full_name']} ({u['blood_type']})")
        count += 1
    except Exception as e:
        print(f"Error inserting {u['full_name']}: {e}")

print(f"Import complete. Added {count} new users.")
