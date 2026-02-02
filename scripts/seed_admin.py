
import os
import sys

# Add parent dir to path to import api.utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

def seed_admin():
    print("Seeding Admin User...")
    
    # Check if admin exists
    res = supabase.table("villingili_admin_users").select("*").eq("username", "admin").execute()
    
    if res.data:
        print("Admin user 'admin' already exists.")
        return

    # Create Admin
    # Note: telegram_id is required and unique. providing a dummy placeholder.
    admin_data = {
        "telegram_id": 999999999, # Dummy ID for local admin
        "username": "admin",
        "phone_number": "admin", # Allow login with phone='admin' as well
        "password": "admin"
    }
    
    try:
        data = supabase.table("villingili_admin_users").insert(admin_data).execute()
        print("Successfully created admin user: admin / admin")
    except Exception as e:
        print(f"Error creating admin: {e}")

if __name__ == "__main__":
    seed_admin()
