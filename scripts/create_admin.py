import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY") # Service Role Key
supabase = create_client(url, key)

email = os.environ.get("ADMIN_EMAIL", "admin@blood.com")
password = os.environ.get("ADMIN_PASSWORD", "admin")

print(f"Creating user: {email}")

try:
    # Use Admin API to create user
    user = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    print(f"User created! ID: {user.user.id}")
except Exception as e:
    print(f"Error: {e}")
