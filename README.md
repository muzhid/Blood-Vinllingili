# Blood Donation-Siwad Portal (Community Edition)

## Introduction 🏥
This project is a **Free and Open Source** Blood Donation Management System designed for local communities. It bridges the gap between blood requesters and donors using the most common communication tool: **Telegram**.

> **Note:** This project was originally developed to serve the **Siwad** community. 🏝️

Instead of complex apps that users won't install, this system lives where your community already is. It combines a **Telegram Bot** for donors/requesters, a **Telegram Group** for admins, a **Telegram Channel** for public alerts, and a **Web Dashboard** for advanced management.

**Built for Communities.** To ensure every request is seen and every donor is reachable.

---

## 🚀 How It Works

### 1. User Workflow (Private Chat) 👤
- **Find Donors:** Users can request blood by chatting with the bot. The bot uses **AI** to parse their request (e.g., "Need A+ blood in Male' urgent").
- **Results:** The bot instantly replies with a list of matching donors (Name & Phone).
- **Registration:** Donors can register by sending their ID Card photo. The bot uses **AI (OCR)** to scan the card and fill in details automatically.

### 2. Admin Group (Administrative Command Center) 🛡️
Admins manage the system directly from a dedicated Telegram Group.
- **Approvals:** When a user requests to be removed or activated, alerts are sent here.
- **Scan & Add:** Admins can send a photo of a donor's ID card to the group, and the bot will auto-register them.
- **Commands:**
    - `list`: Shows all registered donors grouped by blood type.
    - `A+` (or any blood type): Searching for specific blood type instantly lists matching donors.
    - `/admin_access`: Generates temporary credentials to login to the Web Dashboard.
    - `/reset_password`: Resets dashboard password.

### 3. Telegram Channel (Public Alerts) 📢
- **Broadcast:** Every approved blood request is automatically posted to a public Telegram Channel.
- **Volunteer:** Registered donors in the channel can click **"I Can Help"** on the post to instantly connect with the requester.

### 4. Web Dashboard (Central Management) 💻
A powerful React-based dashboard for advanced tasks:
- **User Management:** Add, Edit, Delete, or Ban users.
- **Search:** Global search for donors.
- **Settings:** Manage Admin accounts.

---

## 🛠️ Architecture
This project is built on a modern, scalable stack suitable for free deployment on community tiers.
- **Frontend:** React + Vite + Tailwind CSS (Fast, Responsive).
- **Backend:** Python FastAPI (High performance, Easy to extend).
- **Database:** Supabase (PostgreSQL with Realtime capabilities).
- **Bot:** Python-based Telegram Bot API (Telebot).
- **AI:** OpenAI GPT-4o-mini (For intelligent text parsing and ID Card OCR).

---

## 📦 Setup Guide

### Prerequisites
- **Node.js** & **Python 3.9+** installed.
- A **Supabase** Project (Free Tier).
- A **Telegram Bot** (from @BotFather).
- An **OpenAI API Key**.

### 1. Clone & Install
```bash
git clone https://github.com/your-repo/blood-donation-bot.git
cd blood-donation-bot

# Install Backend Deps
pip install -r requirements.txt

# Install Frontend Deps
cd frontend
npm install
cd ..
```

### 2. Database Setup (Supabase)
1.  Go to your Supabase Project -> **SQL Editor**.
2.  Copy contents of `supabase/schema.sql` and run it (Creates tables).
3.  Copy contents of `supabase/admin_schema.sql` and run it (Creates Admin table).
4.  Go to **Project Settings -> API** to find your Keys (`anon public` and `service_role secret`).

### 3. Environment Variables
Create a `.env` file in the root directory.
**Important:** When deploying to Vercel, add ALL these keys in the **Vercel Dashboard -> Settings -> Environment Variables**.

```ini
# Backend Secrets (Used by Python API)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key      # MUST be Service Role Key (for RLS bypass)
OPENAI_API_KEY=sk-proj-...              # For AI Text Parsing & ID OCR
TELEGRAM_BOT_TOKEN=123456:ABC...        # From @BotFather
TELEGRAM_CHANNEL_ID=-100xxxxxxxxxx      # ID of your Public Channel
TELEGRAM_ADMIN_GROUP_ID=-100xxxxxxxxxx  # ID of your Admin Group

# Frontend Secrets (Used by React Website)
VITE_SUPABASE_URL=https://your-project.supabase.co  # Same as SUPABASE_URL
VITE_SUPABASE_ANON_KEY=your_anon_public_key         # MUST be Anon Public Key
```

### 4. Run Locally
> [!IMPORTANT]
> **Bot Permissions:**  
> You MUST make your Bot an **Admin** in both the **Admin Group** and the **Telegram Channel**.
> - In Group: To allow it to read messages (ID Cards) and delete commands.
> - In Channel: To allow it to post broadcast messages.
> - Ensure "Privacy Mode" is disabled via @BotFather if you want it to see all group messages.

**Backend & Bot:**
```bash
# Terminal 1
uvicorn api.index:app --reload --port 8000
# Terminal 2
python local_bot.py
```
**Frontend:**
```bash
# Terminal 3 (in /frontend)
npm run dev
```

### 4. Deploy to Vercel
The project is optimized for **Vercel**.
1. Install Vercel CLI (`npm i -g vercel`).
2. Run `vercel`.
3. Add Environment Variables in Vercel Dashboard.
4. Set up a Cron Job (optional) for cleanup.

---

## 🤝 Contact & Support
This project is a labor of love for community welfare.
- **Email:** `muzhid@gmail.com`
- **License:** Free for Community Use (Non-Commercial).

**Note:** This software should **NOT** be used for profit-making. It is intended to save lives and support local blood donation networks freely.
