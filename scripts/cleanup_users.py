import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load env vars from the root .env file
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Supabase credentials (SUPABASE_URL, SUPABASE_KEY) not found in environment.")
    print("Make sure .env file exists and is readable.")
    sys.exit(1)

print(f"Connecting to Supabase at {url}...")
try:
    supabase = create_client(url, key)
except Exception as e:
    print(f"Failed to create Supabase client: {e}")
    sys.exit(1)

try:
    # 1. Check count
    print("Checking current user count...")
    # Select all rows
    res = supabase.table("users").select("*", count="exact").execute()
    count = res.count
    print(f"Current user count: {count}")

    if count == 0:
        print("Table 'users' is already empty.")
        sys.exit(0)

    # 1.5 Delete REQUESTS (FK Constraint)
    print("Deleting requests (to satisfy FK constraints)...")
    # Using created_at to avoid ID type issues (UUID vs Int)
    req_del = supabase.table("requests").delete().gt("created_at", "1970-01-01T00:00:00+00:00").execute()
    print(f"Deleted {len(req_del.data) if req_del.data else 0} requests.")

    # 2. Delete ALL users
    print("Deleting all users...")
    
    # Using created_at if available, or just neq telegram_id 0 if we are sure it is BigInt.
    # Users usually have created_at too. Let's try created_at first.
    # If created_at is missing in users, we fall back to telegram_id > 0
    try:
         del_res = supabase.table("users").delete().gt("created_at", "1970-01-01T00:00:00+00:00").execute()
    except:
         print("created_at not found in users, trying telegram_id...")
         # telegram_id is BigInt (int8), so neq 0 should logically work, but let's try gt -1.
         del_res = supabase.table("users").delete().gt("telegram_id", -1).execute()
    
    deleted_count = len(del_res.data) if del_res.data else 0
    print(f"Successfully deleted {deleted_count} users.")

except Exception as e:
    print(f"An error occurred during DB operation: {e}")
    sys.exit(1)
