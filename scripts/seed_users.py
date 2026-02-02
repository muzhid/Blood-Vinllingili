
import os
import random
import time
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Add parent dir to path if needed, though we handle imports directly here
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SEXES = ["Male", "Female"]
ISLANDS = ["Male'", "Hulhumale'", "Villingili", "Addu", "Fuvahmulah", "Kulhudhuffushi", "Thinadhoo", "Siwad"]
NAMES_FIRST = ["Ahmed", "Mohamed", "Ali", "Hassan", "Ibrahim", "Abdullah", "Fathimath", "Aishath", "Mariyam", "Aminath", "Zain", "Yusuf", "Sara", "Leena"]
NAMES_LAST = ["Maniku", "Sattar", "Didi", "Rasheed", "Shareef", "Nazeer", "Latheef", "Jameel", "Hussain", "Fulhu"]

def generate_phone():
    # 7-digit random number starting with 9 (Maldives mobile) - 9XXXXXX
    # Increased range to avoid collisions
    return f"9{random.randint(100000, 999999)}"

def generate_id_card():
    # Format: AXXXXXX
    return f"A{random.randint(100000, 999999)}"

def seed_users(count=50):
    print(f"Seeding {count} users to 'villingili_users'...")
    users = []
    
    for i in range(count):
        first = random.choice(NAMES_FIRST)
        last = random.choice(NAMES_LAST)
        full_name = f"{first} {last}"
        
        # Unique telegram ID (simulated)
        # Base it on a fixed high number + index to guarantee uniqueness in this batch
        telegram_id = 1000000000 + (int(time.time()) % 100000) * 100 + i
        
        user = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "phone_number": generate_phone(),
            "blood_type": random.choice(BLOOD_TYPES),
            "sex": random.choice(SEXES),
            "id_card_number": generate_id_card(),
            "address": random.choice(ISLANDS),
            "status": "active",
            "role": "user",
            # Random date in last 2 years or None
            "last_donation_date": (datetime.now() - timedelta(days=random.randint(0, 700))).strftime("%Y-%m-%d") if random.random() > 0.3 else None
        }
        users.append(user)

    try:
        # Insert in batches to be safe
        data = supabase.table("villingili_users").upsert(users).execute()
        print(f"Successfully inserted/updated {len(data.data)} dummy users.")
    except Exception as e:
        print(f"Error seeding users: {e}")

if __name__ == "__main__":
    seed_users()
