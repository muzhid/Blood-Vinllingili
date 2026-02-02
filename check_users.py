from api.utils import get_supabase_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = get_supabase_client()
try:
    print("Querying villingili_users...")
    res = supabase.table("villingili_users").select("*").execute()
    print(f"Count: {len(res.data)}")
    print("Data:", res.data)
except Exception as e:
    print(f"Error: {e}")
