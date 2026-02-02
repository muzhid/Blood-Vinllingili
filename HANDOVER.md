# Blood-Villingili Handover Guide

## Prerequisites
- **Python 3.9+** installed
- **Node.js** installed (for frontend)
- **Supabase Account** (Keys in `.env`)

## How to Run

### 1. Start the Bot & API
Double-click `start_bot.bat`. 
This will open two windows:
1. **API Server** (FastAPI)
2. **Telegram Bot** (Polling Mode)

### 2. Start the Frontend (Optional)
If you want to view the web dashboard:
```bash
cd frontend
npm run dev
```

## Configuration
All settings are in the `.env` file.
- `SUPABASE_URL`: Your Supabase URL
- `TELEGRAM_BOT_TOKEN`: Your Bot Token

## Database Tables
The system uses the following tables (prefixed for safety):
- `villingili_users`
- `villingili_requests`
- `villingili_admin_users`
- `villingili_blacklist`

## 📖 User Manual
A mobile-friendly, printable user guide is available.

- **File Path**: `manual/Guide_With_Images.html`
- **How to Use**:
  1. Open the file in Chrome/Edge on your PC.
  2. Press `Ctrl + P` -> "Save as PDF".
  3. Share the PDF on Telegram/WhatsApp.
- **Features**:
  - Embedded images (no missing files).
  - Optimized for mobile screens (side-by-side layout).
  - "One Slide Per Page" layout for easy reading.

## 📢 Broadcast Feature
- **How it works**: When a blood request is made, it is automatically forwarded to the channel set in `TELEGRAM_CHANNEL_ID`.
- **Note**: The "I Can Help" button has been removed as per request.

## ✅ Recent Fixes
- Removed stale debug prints from `api/index.py`.
- Fixed mobile scrolling issues in the Dashboard tables.
- Standardized database table names (`villingili_...`).

## 🚀 Production Deployment (Live)

- **Admin Portal**: `https://blood-vinllingili.vercel.app`
- **Manuals**: `https://blood-vinllingili.vercel.app/manual/v2/index.html`
- **Bot Name**: `BIOOD-VILLINGILI Donors` (`@villingili_blood_bot`)

### ⚡ Critical Settings
Ensure these are set in Vercel:
1.  `TELEGRAM_ADMIN_GROUP_ID`: `-1003825409576`
2.  `SUPABASE_SERVICE_ROLE_KEY`: (From Supabase -> Settings -> API)

### 🔗 Webhook Setup (Run Once)
To wake up the bot:
```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://blood-vinllingili.vercel.app/api/webhook
```

## 📂 Manuals
User manuals are located in `manual/v2/index.html`. Open this file to access guides for Admins, Nurses, and the Public.
