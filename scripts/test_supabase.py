import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

print(f"Testing connection to {url}...")
print(f"Key preview: {key[:5]}...")

try:
    supabase = create_client(url, key)
    # Try a simple select. 'users' table might be empty, but query should succeed.
    # We use count to minimize data transfer and just check auth.
    response = supabase.table("users").select("*", count="exact").limit(1).execute()
    print("Connection Successful!")
    print(f"Data: {response}")
except Exception as e:
    print(f"Connection Failed: {e}")
