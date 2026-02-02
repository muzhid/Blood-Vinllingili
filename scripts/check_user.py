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

print("Searching for 'Zahiya'...")
# Case insensitive search usually ilike
res = supabase.table("users").select("*").ilike("full_name", "%Zahiya%").execute()

if res.data:
    print(f"Found {len(res.data)} users:")
    for u in res.data:
        print(f" - Name: {u.get('full_name')}")
        print(f" - Phone: {u.get('phone_number')}")
        print(f" - Blood: {u.get('blood_type')}")
        print(f" - Status: {u.get('status')}")
        print(f" - ID Card: {u.get('id_card_number')}")
else:
    print("No user found with name like 'Zahiya'")

print("\nRunning 'List' query clone...")
# Run the exact query the bot runs
res2 = supabase.table("users").select("full_name, phone_number, blood_type").neq("blood_type", "null").execute()
found_in_list = False
for u in res2.data:
    if "zahiya" in (u.get("full_name") or "").lower():
        print(f"Found in LIST query: {u}")
        found_in_list = True

if not found_in_list:
    print("Not found in 'List' query execution either.")
