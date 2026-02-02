import sqlite3
import os

DB_PATH = "blood_donation.db"

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        full_name TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        alternate_phones TEXT,
        blood_type TEXT,
        sex TEXT,
        id_card_number TEXT,
        address TEXT,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active',
        last_donation_date TEXT,
        username TEXT,
        pending_request_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Requests Table
    # SQLite doesn't have UUID/BigInt native types like Postgres, use TEXT/INTEGER
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY,
        requester_id INTEGER NOT NULL,
        blood_type TEXT,
        location TEXT,
        urgency TEXT,
        is_active BOOLEAN DEFAULT 1,
        donors_found INTEGER DEFAULT 0,
        telegram_message_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(requester_id) REFERENCES users(telegram_id)
    )
    ''')

    # 3. Admin Users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        phone_number TEXT,
        password TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 4. Blacklist (from schema)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blacklist (
        phone_number TEXT PRIMARY KEY,
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_is_active ON requests(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_blood_type ON users(blood_type)')

    # Seed Admin User
    print("Seeding default admin user...")
    cursor.execute('''
        INSERT INTO admin_users (telegram_id, username, phone_number, password, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (123456789, 'admin', '9607770000', 'admin123'))

    conn.commit()
    conn.close()
    print(f"Database {DB_PATH} initialized successfully.")

if __name__ == "__main__":
    init_db()
