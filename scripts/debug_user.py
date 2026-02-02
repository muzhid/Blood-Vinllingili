import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY")
    exit(1)

supabase = create_client(url, key)

target_phone = "7779048"
print(f"Searching for phone: {target_phone}...")

res = supabase.table("users").select("*").eq("phone_number", target_phone).execute()

if res.data:
    user = res.data[0]
    print(f"FOUND USER:")
    print(f" - Name: {user.get('full_name')}")
    print(f" - Phone: {user.get('phone_number')}")
    print(f" - Telegram ID: {user.get('telegram_id')}")
    print(f" - Blood Type: {user.get('blood_type')}")
    print(f" - Status: {user.get('status')}")
    print(f" - ID Card: {user.get('id_card_number')}")
    
    if not user.get('blood_type'):
        print("\nDIAGNOSIS: Blood Type is MISSING. This causes the 'not registered' error at line 651.")
    else:
        print("\nDIAGNOSIS: Blood Type is PRESENT.")
        
    if str(user.get('telegram_id')).startswith('pending_') or int(user.get('telegram_id')) < 10000000000: 
        # ID Card hashes are usually smaller or different, real TGs are > 100000000 usually?
        # Actually real TG IDs are positive integers approx 10 digits.
        # Fake hashes in code: int(hashlib.sha256...) % (10**12). They can be big.
        # But if it was scanned, it might be a 'fake' ID.
        pass
else:
    print("User NOT FOUND by phone number.")
