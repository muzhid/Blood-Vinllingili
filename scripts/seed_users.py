import os
import random
import time
from api.local_db import LocalDB
import sys
# Add parent dir to path to find api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

supabase = LocalDB()

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SEXES = ["Male", "Female"]
ISLANDS = ["Male'", "Hulhumale'", "Villingili", "Addu", "Fuvahmulah", "Kulhudhuffushi", "Thinadhoo", "Siwad"]
NAMES_FIRST = ["Ahmed", "Mohamed", "Ali", "Hassan", "Ibrahim", "Abdullah", "Fathimath", "Aishath", "Mariyam", "Aminath", "Zain", "Yusuf", "Sara", "Leena"]
NAMES_LAST = ["Maniku", "Sattar", "Didi", "Rasheed", "Shareef", "Nazeer", "Latheef", "Jameel", "Hussain", "Fulhu"]

def generate_phone():
    # 7-digit random number starting with 900 to ensure it's fake
    return f"900{random.randint(1000, 9999)}"

def generate_id_card():
    # Format: AXXXXXX
    return f"A{random.randint(100000, 999999)}"

def seed_users(count=30):
    print(f"Seeding {count} users...")
    users = []
    
    for i in range(count):
        first = random.choice(NAMES_FIRST)
        last = random.choice(NAMES_LAST)
        full_name = f"{first} {last}"
        
        # Unique telegram ID (simulated)
        telegram_id = int(str(time.time()).replace('.', '')[-9:]) + i
        
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
            "last_donation_date": f"202{random.randint(4,5)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}" if random.random() > 0.3 else None
        }
        users.append(user)

    try:
        # Insert in batches to be safe
        data = supabase.table("users").upsert(users).execute()
        print(f"Successfully inserted/updated {len(data.data)} users.")
    except Exception as e:
        print(f"Error seeding users: {e}")

if __name__ == "__main__":
    seed_users()
