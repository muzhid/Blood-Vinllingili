from fastapi import FastAPI, Request
import asyncio
from .utils import get_supabase_client, parse_request_with_ai, send_telegram_message
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for local development
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status

# Security Config
SECRET_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Using Service Key as Secret implies robust secret, or use a dedicated one.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Check for special migration token if needed, or just standard JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Cache
PENDING_SCANS = {}

# --- SERVE FRONTEND (STATIC FILES) ---
# Files are copied to 'static' folder next to this file during build
base_dir = os.path.dirname(os.path.abspath(__file__))
dist_dir = os.path.join(base_dir, "static")

assets_dir = os.path.join(dist_dir, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/api/index")
def home():
    return {"message": "Blood Donation Bot API is running"}

@app.get("/api/users")
def get_users(current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    res = supabase.table("villingili_users").select("*").order("created_at", desc=True).execute()
    return res.data

@app.get("/api/requests")
def get_requests(current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    res = supabase.table("villingili_requests").select("*").order("created_at", desc=True).limit(50).execute()
    requests = res.data
    
    # Manual Join to populate requester info
    for req in requests:
        user_id = req.get("requester_id")
        if user_id:
            user_res = supabase.table("villingili_users").select("full_name, phone_number").eq("telegram_id", user_id).execute()
            if user_res.data:
                req["requester"] = user_res.data[0]
            else:
                 req["requester"] = None
    return requests

@app.get("/api/debug_files")
def debug_files():
    import os
    files = []
    # Search for index.html specifically
    target = "index.html"
    found = []
    
    for root, dirs, filenames in os.walk("/var/task"): # Search everywhere in Task
        for filename in filenames:
            path = os.path.join(root, filename)
            files.append(path)
            if filename == target:
                found.append(path)
                
    return {"found": found, "total_files": len(files), "sample": files[:50], "cwd": os.getcwd()}




@app.get("/api/cron_expire")
def cron_expire():
    supabase = get_supabase_client()
    if not supabase:
        return {"status": "error", "message": "DB failed"}
    
    # 1. Find active requests created > 30 mins ago
    # PostgREST syntax for timestamp comparison is tricky raw, 
    # but we can select all active and filter in python for simplicity if low volume,
    # or use proper filters: created_at -> lt -> now() - interval '30 minutes'
    # Supabase/PostgREST doesn't support easy interval math in 'lt' param directly without a function/view.
    # For MVP: Fetch all active, filter loop.
    
    try:
        active_reqs = supabase.table("villingili_requests").select("*").eq("is_active", True).execute()
        if not active_reqs.data:
            return {"status": "ok", "count": 0}
            
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for req in active_reqs.data:
            created_at = datetime.fromisoformat(req["created_at"].replace('Z', '+00:00'))
            if now - created_at > timedelta(minutes=30):
                # Expire it
                supabase.table("villingili_requests").update({"is_active": False}).eq("id", req["id"]).execute()
                expired_count += 1
                
                # Update Telegram Message
                if req.get("telegram_message_id") and os.environ.get("TELEGRAM_CHANNEL_ID"):
                    try:
                         # We need to import edit_telegram_message logic
                         # Re-fetching utils here if needed or relying on global scope if merged
                         from .utils import edit_telegram_message 
                         chan_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                         new_text = (
                             f"⏳ <b>EXPIRED REQUEST</b>\n"
                             f"Type: {req.get('blood_type')}\n"
                             f"Location: {req.get('location')}\n"
                             f"Requester: (Expired)"
                         )
                         edit_telegram_message(chan_id, req["telegram_message_id"], new_text)
                    except Exception as e:
                        print(f"Failed to edit msg: {e}")
                        
        return {"status": "ok", "expired": expired_count}

    except Exception as e:
        print(f"Cron Error: {e}")
        return {"status": "error", "detail": str(e)}

from pydantic import BaseModel
class UserUpdate(BaseModel):
    telegram_id: int
    full_name: str = None
    phone_number: str = None
    blood_type: str = None
    sex: str = None
    address: str = None
    id_card_number: str = None
    role: str = None
    status: str = None

@app.post("/api/update_user")
async def update_user_api(user: UserUpdate, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    if not supabase: return {"error": "DB Failed"}
    
    data = user.dict(exclude_unset=True)
    tid = data.pop("telegram_id")
    
    try:
        # Check Phone Conflict logic (retained)
        if "phone_number" in data:
             phone = data["phone_number"]
             conflict = supabase.table("villingili_users").select("*").eq("phone_number", phone).neq("telegram_id", tid).execute()
             if conflict.data:
                  other_u = conflict.data[0]
                  curr_name = data.get("full_name")
                  if not curr_name:
                       curr_u = supabase.table("villingili_users").select("full_name").eq("telegram_id", tid).execute()
                       if curr_u.data: curr_name = curr_u.data[0].get('full_name')
                  
                  c_low = (curr_name or "").lower().strip()
                  o_low = (other_u.get("full_name") or "").lower().strip()
                  name_match = (c_low == o_low)
                  c_id = data.get("id_card_number")
                  if not c_id:
                       if curr_u and curr_u.data: c_id = curr_u.data[0].get("id_card_number")
                  o_id = other_u.get("id_card_number")
                  id_conflict = False
                  if c_id and o_id and c_id.upper() != o_id.upper(): id_conflict = True
                  
                  if name_match and not id_conflict:
                       old_id = other_u['telegram_id']
                       supabase.table("villingili_users").update({"phone_number": f"{phone}_old_{old_id}"}).eq("telegram_id", old_id).execute()
                       supabase.table("villingili_requests").update({"requester_id": tid}).eq("requester_id", old_id).execute()
                       supabase.table("villingili_users").delete().eq("telegram_id", old_id).execute()
                  else:
                       msg = f"Phone taken by {other_u.get('full_name')}"
                       if id_conflict: msg += " (ID Mismatch)"
                       return {"status": "error", "detail": msg}

        supabase.table("villingili_users").update(data).eq("telegram_id", tid).execute()
        return {"status": "ok"}
    except Exception as e:
        print(f"Update Error: {e}")
        return {"status": "error", "detail": str(e)}

# ---------------- ADMIN AUTH ----------------
import secrets

class AdminLogin(BaseModel):
    username: str
    password: str

@app.post("/api/admin_login")
async def admin_login_api(creds: AdminLogin):
    try:
        supabase = get_supabase_client()
        if not supabase: return {"error": "DB Failed"}
        
        # 1. Fetch user by Phone OR Username
        # We fetch the HASHED password (or plain text if not migrated yet)
        user_res = supabase.table("villingili_admin_users").select("*").eq("phone_number", creds.username).execute()
        if not user_res.data:
             user_res = supabase.table("villingili_admin_users").select("*").eq("username", creds.username).execute()
        
        if not user_res.data:
            return {"status": "error", "message": "User not found"}
            
        admin = user_res.data[0]
        stored_pw = admin["password"]
        
        # 2. Verify Password (Handle Legacy Plain Text vs Bcrypt)
        is_valid = False
        try:
            # Try verifying as hash
            if verify_password(creds.password, stored_pw):
                is_valid = True
        except:
            # Fallback for legacy plain text (temporary migration logic)
            if stored_pw == creds.password:
                is_valid = True
                # Auto-migrate to hash?!
                new_hash = get_password_hash(stored_pw)
                supabase.table("villingili_admin_users").update({"password": new_hash}).eq("id", admin["id"]).execute()
        
        if is_valid:
            # 3. Generate Token
            access_token = create_access_token(data={"sub": admin["username"], "role": "admin"})
            
            return {
                "status": "ok",
                "access_token": access_token, 
                "token_type": "bearer",
                "user": {
                    "username": admin["username"],
                    "phone_number": admin["phone_number"],
                    "role": "admin",
                    "telegram_id": admin["telegram_id"]
                }
            }
            
        return {"status": "error", "message": "Invalid Password"}
    except Exception as e:
        print(f"Login Error: {e}")
        return {"status": "error", "message": f"Server Error: {str(e)}"}

@app.get("/api/get_admins")
async def get_admins_api(current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    if not supabase:
        print("DB Connection Failed in get_admins")
        return []
        
    # Security: This should verify header token actually, but we are skipping for MVP speed
    # Assuming Frontend only calls this if logged in. 
    # (In prod, add Auth Header check)
    res = supabase.table("villingili_admin_users").select("telegram_id, username, phone_number, password, created_at").execute() 
    
    if not res.data: return []

    admins = res.data
    for admin in admins:
        if admin.get("phone_number") == "Linked" and admin.get("telegram_id"):
            # Try to resolve
            try:
                user_res = supabase.table("villingili_users").select("phone_number").eq("telegram_id", admin["telegram_id"]).execute()
                if user_res.data and user_res.data[0].get("phone_number"):
                     real_phone = user_res.data[0]["phone_number"]
                     admin["phone_number"] = real_phone
                     # Self-heal
                     supabase.table("villingili_admin_users").update({"phone_number": real_phone}).eq("telegram_id", admin["telegram_id"]).execute()
            except:
                pass
                
    return admins

class PasswordUpdate(BaseModel):
    username: str
    new_password: str

@app.post("/api/update_password")
async def update_password_api(body: PasswordUpdate, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    if not supabase: return {"error": "DB Failed"}

    # Validation
    if len(body.new_password) < 4:
         return {"status": "error", "message": "Password must be at least 4 characters"}
    import re
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", body.new_password):
         return {"status": "error", "message": "Password must contain at least one special character"}

    # Update (Security: Should verify user exists first, but update works too)
    # We trust the username matches the session.
    # Logic update: Use phone_number as identifier if provided, else username? 
    # For now, we assume frontend sends phone_number in 'username' field OR we add phone field.
    # Better: Update backend to accept phone_number.
    
    identifier = body.username 
    # If frontend sends phone in username field:
    # HASH THE PASSWORD BEFORE SAVING!
    hashed_pw = get_password_hash(body.new_password)
    
    res = supabase.table("villingili_admin_users").update({"password": hashed_pw}).eq("phone_number", identifier).execute()
    
    if res.data:
        return {"status": "ok"}
    # Fallback try username if phone failed (migration support)
    res = supabase.table("villingili_admin_users").update({"password": hashed_pw}).eq("username", identifier).execute()
    if res.data: return {"status": "ok"}

    return {"status": "error", "message": "User not found"}

class AdminCreate(BaseModel):
    username: str
    phone_number: str

@app.post("/api/create_admin")
async def create_admin_api(body: AdminCreate, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    if not supabase: return {"error": "DB Failed"}
    
    # Check if exists (Check PHONE)
    exists = supabase.table("villingili_admin_users").select("id").eq("phone_number", body.phone_number).execute()
    if exists.data: return {"status": "error", "message": "Phone Number already registered"}
    
    from datetime import datetime
    # Generate placeholder Telegram ID (required by DB schema)
    # We use a timestamp-based ID to ensure uniqueness for manual users
    fake_id = int(datetime.now().timestamp() * 1000)
    
    # Hash default password
    hashed_pw = get_password_hash("Password1")
    
    data = {
        "username": body.username,
        "phone_number": body.phone_number,
        "password": hashed_pw, # Hashed!
        "telegram_id": fake_id,
        "created_at": datetime.now().isoformat()
    }
    try:
        supabase.table("villingili_admin_users").insert(data).execute()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def process_update(data):
    from .utils import send_telegram_message
    supabase = get_supabase_client()
    print(f"DEBUG: process_update called with keys: {list(data.keys())}", flush=True)
    if not supabase:
        print("DB connection failed")
        return

    global PENDING_SCANS

    # Handle Callback Queries (Buttons)
    if "callback_query" in data:
        cb = data["callback_query"]
        cb_id = cb["id"]
        chat_id = cb["message"]["chat"]["id"]
        print(f'DEBUG: Chat ID={chat_id}')
        user_id = cb["from"]["id"]
        data_str = cb.get("data")
        print(f"DEBUG: Callback received: {data_str} from {user_id}")
        
        # Check registration
        try:
            user_query = supabase.table("villingili_users").select("*").eq("telegram_id", user_id).execute()
            user = user_query.data[0] if user_query.data else None
        except Exception as e:
            print(f"DEBUG: User check failed: {e}")
            return
        
        if not user:
             # If channel interaction or user hasn't started bot, send alert instead of message
             # Redirect to Bot Start
             from .utils import answer_callback_query
             answer_callback_query(cb_id, text="You are not a registered donor. Contact admin to register", show_alert=True)
             return
             
        if not user:
             send_telegram_message(user_id, "Please register first by sending your contact to the bot.")
             return

        # Check if BANNED
        if user.get("status") == "banned":
             from .utils import answer_callback_query
             answer_callback_query(cb_id, text="🚫 You are banned from using this service.", show_alert=True)
             return

        if data_str.startswith("force_update_"):
            fake_tg_id = data_str.split("_")[2]
            # global PENDING_SCANS (Declared at top)
            user_data = PENDING_SCANS.get(fake_tg_id)
            
            if user_data:
                # Execute Update
                supabase.table("villingili_users").upsert(user_data).execute()
                # Clean cache
                del PENDING_SCANS[fake_tg_id]
                
                # Proceed to Confirm
                msg_text = (
                    f"✅ <b>User Updated!</b>\n"
                    f"👤 Name: {user_data['full_name']}\n"
                    f"Is this correct?"
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ Confirm & Select Blood Group", "callback_data": f"confirm_id_{user_data['telegram_id']}" }]
                    ]
                }
                from .utils import edit_telegram_message
                msg_id = cb["message"]["message_id"]
                edit_telegram_message(chat_id, msg_id, msg_text, reply_markup=keyboard)
            else:
                send_telegram_message(chat_id, "⚠️ Session expired. Please scan again.")
            return

        if data_str.startswith("cancel_update_"):
            fake_tg_id = data_str.split("_")[2]
            if str(fake_tg_id) in PENDING_SCANS:
                del PENDING_SCANS[str(fake_tg_id)]
            
            from .utils import edit_telegram_message
            msg_id = cb["message"]["message_id"]
            edit_telegram_message(chat_id, msg_id, "❌ <b>Update Cancelled.</b>")
            return

        if data_str.startswith("confirm_id_"):
            fake_tg_id = data_str.split("_")[2]
            # Show Blood Buttons
            msg_text = "🩸 <b>Please Select Blood Group:</b>"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "A+", "callback_data": f"set_blood_{fake_tg_id}_A+"}, {"text": "A-", "callback_data": f"set_blood_{fake_tg_id}_A-"}],
                    [{"text": "B+", "callback_data": f"set_blood_{fake_tg_id}_B+"}, {"text": "B-", "callback_data": f"set_blood_{fake_tg_id}_B-"}],
                    [{"text": "O+", "callback_data": f"set_blood_{fake_tg_id}_O+"}, {"text": "O-", "callback_data": f"set_blood_{fake_tg_id}_O-"}],
                    [{"text": "AB+", "callback_data": f"set_blood_{fake_tg_id}_AB+"}, {"text": "AB-", "callback_data": f"set_blood_{fake_tg_id}_AB-"}],
                ]
            }
            from .utils import edit_telegram_message
            msg_id = cb["message"]["message_id"]
            edit_telegram_message(chat_id, msg_id, msg_text, reply_markup=keyboard)
            return

        if data_str.startswith("set_blood_"):
            # ID Card Registration Flow: parse stored ID and blood type
            parts = data_str.split("_")
            # format: set_blood_{fake_id}_{type}
            # caution: fake_id might be large integer
            if len(parts) >= 4:
                fake_id = parts[2]
                b_type = parts[3]
                
                # Update User
                supabase.table("villingili_users").update({"blood_type": b_type}).eq("telegram_id", fake_id).execute()
                
                # Fetch User Data (Name & Phone)
                u_res = supabase.table("villingili_users").select("full_name", "phone_number").eq("telegram_id", fake_id).execute()
                u_data = u_res.data[0] if u_res.data else {}
                u_name = u_data.get("full_name", "User")
                phone = u_data.get("phone_number")
                
                # CHECK IF VALID PHONE EXISTS
                if phone and not phone.startswith("pending") and len(phone) >= 7:
                    # Ask to Keep or Change
                    msg_text = (
                        f"👤 <b>{u_name}</b>\n"
                        f"🩸 Blood Type: <b>{b_type}</b>\n\n"
                        f"📞 <b>Existing Phone:</b> <code>{phone}</code>\n"
                        f"Do you want to change it?"
                    )
                    keyboard = {
                        "inline_keyboard": [
                             [{"text": f"✅ Keep {phone}", "callback_data": f"keep_phone_{fake_id}"}],
                             [{"text": "✏️ Change Number", "callback_data": f"change_phone_{fake_id}"}]
                        ]
                    }
                else:
                    # No valid phone, ask for input
                    msg_text = (
                        f"👤 <b>{u_name}</b>\n"
                        f"🩸 Blood Type Set to <b>{b_type}</b>.\n"
                        f"👇 Reply to this message with Mobile Number.\n"
                        f"<span class='tg-spoiler'>REF:{fake_id}</span>" 
                    )
                    reply_markup = {"force_reply": True, "input_field_placeholder": "7xxxxxx"}
                    send_telegram_message(chat_id, msg_text, reply_markup=reply_markup)
                    
                    # Answer callback
                    from .utils import answer_callback_query
                    answer_callback_query(cb_id, text="Blood Type Saved")
                    return

                # Send Message (for Keep/Change flow)
                from .utils import edit_telegram_message
                msg_id = cb["message"]["message_id"]
                edit_telegram_message(chat_id, msg_id, msg_text, reply_markup=keyboard)
            return

        if data_str.startswith("keep_phone_"):
            # Finishes update
            fake_id = data_str.split("_")[2]
            # Just confirmation message
            from .utils import edit_telegram_message
            msg_id = cb["message"]["message_id"]
            edit_telegram_message(chat_id, msg_id, "✅ <b>Update Complete!</b>\nUser details saved.")
            return

        if data_str.startswith("change_phone_"):
            fake_id = data_str.split("_")[2]
            # Prompt for Phone
            msg_text = (
                f"👇 <b>Reply to this message with NEW Mobile Number.</b>\n"
                f"<span class='tg-spoiler'>REF:{fake_id}</span>" 
            )
            reply_markup = {"force_reply": True, "input_field_placeholder": "7xxxxxx"}
            send_telegram_message(chat_id, msg_text, reply_markup=reply_markup)
            
            # Update previous message to say "Changing..."
            from .utils import edit_telegram_message
            msg_id = cb["message"]["message_id"]
            edit_telegram_message(chat_id, msg_id, "✏️ <b>Enter New Number below...</b>")
            return

        # 0. Register as Donor (Switch from seeker flow)
        if data_str == "reg_donor":
            from .utils import answer_callback_query, check_and_prompt_missing_info
            answer_callback_query(cb_id, "Switching to Donor Registration...")
            check_and_prompt_missing_info(user_id, user)
            return

        # 0.5 Request Blood (Seeker Flow) - IMMEDIATE ACTION
        if data_str.startswith("req_blood_"):
            blood_type = data_str.split("_")[2]
            # Ensure imports are available - GLOBAL IMPORT IS SUFFICIENT
            from .utils import answer_callback_query, edit_telegram_message
            answer_callback_query(cb_id, "Fetching Donors...")
            
            # 1. Fetch & Send Donor List
            try:
                # Exclude self? .neq("telegram_id", user_id)
                donors = supabase.table("villingili_users").select("full_name, phone_number").eq("blood_type", blood_type).eq("status", "active").execute()
                donor_list = donors.data
                
                if donor_list:
                    list_text = f"🩸 <b>Found {len(donor_list)} Donors for {blood_type}:</b>\n\n"
                    for d in donor_list:
                        list_text += f"👤 {d.get('full_name')} - ☎️ {d.get('phone_number')}\n"
                else:
                    list_text = f"🩸 <b>No active donors found for {blood_type}</b> yet."
                
                # Send List Privately
                # Use edit for the button message or new message? User said "send list". 
                # Let's edit the "Registration Complete" msg to show the list or just send new one?
                # Editing might be cleaner.
                edit_telegram_message(chat_id, cb["message"]["message_id"], list_text)
                
            except Exception as e:
                print(f"Donor Fetch Error: {e}")
                send_telegram_message(chat_id, "⚠️ Error fetching donor list.")

            # 2. Auto-Create Request & Broadcast (Location: Not Specified)
            location = "Not Specified"
            urgency = "Normal"
            
            try:
                req_data = {
                     "requester_id": user_id,
                     "blood_type": blood_type,
                     "location": location,
                     "urgency": urgency,
                     "is_active": True
                }
                res = supabase.table("villingili_requests").insert(req_data).execute()
                req_id = res.data[0]['id']
                
                # Broadcast to Channel
                import os
                channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                if channel_id:
                     from .utils import format_blood_request_message
                     msg_text = format_blood_request_message(blood_type, location, urgency, user['full_name'], user.get('phone_number'))
                     keyboard = {
                          "inline_keyboard": [[
                              {"text": "🙋♂️ I Can Help", "callback_data": f"help_{req_id}"}
                          ]]
                     }
                     # Send to channel
                     sent = send_telegram_message(channel_id, msg_text)
                     
                     # Store message ID
                     if sent and sent.get("ok"):
                        msg_id = sent["result"]["message_id"]
                        supabase.table("villingili_requests").update({"telegram_message_id": msg_id}).eq("id", req_id).execute()

                # send_telegram_message(chat_id, f"✅ Request Sent to Channel")
                return

            except Exception as e:
                print(f"Request Creation Error: {e}")
                # Don't spam error if list was sent
                return
            
            return

        # 0.6 Finalize Request (Location Selected) - DEPRECATED / UNUSED
        if data_str.startswith("req_loc_"):
             return # Disabled logic

        if data_str.startswith("admin_set_blood_"):
            parts = data_str.split("_")
            # format: admin_set_blood_{fake_id}_{type}
            if len(parts) >= 5:
                fake_id = parts[3]
                b_type = parts[4]
                
                # Update User Draft
                supabase.table("villingili_users").update({"blood_type": b_type}).eq("telegram_id", fake_id).execute()
                
                
                # Fetch Data for Confirmation
                print(f"DEBUG: Fetching user for confirmation: {fake_id}")
                try:
                    u_res = supabase.table("villingili_users").select("full_name, id_card_number, address").eq("telegram_id", fake_id).execute()
                except Exception as e:
                    print(f"DEBUG: User Update Fetch Error: {e}")
                    send_telegram_message(chat_id, "⚠️ Error fetching user data. Please scan again.")
                    return

                if u_res.data:
                    u = u_res.data[0]
                    # Ask for Phone
                    msg_text = (
                        f"✅ <b>Details Confirmed</b>\n\n"
                        f"👤 Name: {u.get('full_name')}\n"
                        f"🆔 ID: {u.get('id_card_number')}\n"
                        f"🩸 Blood: <b>{b_type}</b>\n\n"
                        f"👇 <b>Reply to this message with Donor's Phone Number (7 Digits).</b>\n"
                        f"<span class='tg-spoiler'>REF:{fake_id}</span>"
                    )
                    reply_markup = {"force_reply": True}
                    
                    from .utils import answer_callback_query, edit_telegram_message, send_telegram_message
                    answer_callback_query(cb_id, "Blood Type Saved")
                    
                    # We can't edit a message to have force_reply (Telegram restriction, usually needs new message).
                    # Actually we can edit the text, but force_reply is an output_message_option, not inline keyboard. 
                    # ForceReply only works on SEND message.
                    # So we delete (or edit to 'Saved') and SEND new one.
                    
                    edit_telegram_message(chat_id, cb["message"]["message_id"], f"✅ <b>Blood Type: {b_type} Selected.</b>")
                    send_telegram_message(chat_id, msg_text, reply_markup=reply_markup)
            return

        if data_str.startswith("set_blood_"):
            # ID Card Registration Flow: parse stored ID and blood type
            from .utils import answer_callback_query
            answer_callback_query(cb_id)
            
            b_type = data_str.split("_")[2]
            supabase.table("villingili_users").update({"blood_type": b_type}).eq("telegram_id", user_id).execute()
            
            # CHECK FOR PENDING REQUEST (Deferred Help)
            u_res = supabase.table("villingili_users").select("full_name, phone_number, pending_request_id").eq("telegram_id", user_id).single().execute()
            if u_res.data and u_res.data.get("pending_request_id"):
                p_req_id = u_res.data["pending_request_id"]
                
                # Execute Help Logic
                try:
                    req_query = supabase.table("villingili_requests").select("*").eq("id", p_req_id).execute()
                    if req_query.data:
                        req = req_query.data[0]
                        requester_id = req["requester_id"]
                        
                        # Exchange Info
                        requester_info = supabase.table("villingili_users").select("full_name, phone_number").eq("telegram_id", requester_id).single().execute()
                        if requester_info.data:
                            r_name = requester_info.data.get("full_name")
                            r_phone = requester_info.data.get("phone_number")
                            d_name = u_res.data.get("full_name")
                            d_phone = u_res.data.get("phone_number")
                            
                            # To Donor
                            send_telegram_message(chat_id, f"✅ <b>Blood Type Saved!</b>\n\n✅ <b>Thanks for helping!</b>\nContact Requester: {r_name} - {r_phone}")
                            
                            # To Requester
                            if str(requester_id) != str(user_id):
                                send_telegram_message(requester_id, f"🦸♂️ <a href='tg://user?id={user_id}'>{d_name}</a> offered to help!\nPhone: {d_phone}")
                            
                            # Update Count & Notify Channel
                            new_count = (req.get("donors_found") or 0) + 1
                            supabase.table("villingili_requests").update({"donors_found": new_count}).eq("id", p_req_id).execute()
                            
                            import os
                            channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                            if channel_id:
                                send_telegram_message(channel_id, f"🦸♂️ <b>{d_name}</b> offered to help a pending request!")
                                
                            # Clear Pending
                            supabase.table("villingili_users").update({"pending_request_id": None}).eq("telegram_id", user_id).execute()
                            return
                except Exception as e:
                    print(f"Deferred Help Error: {e}")

            # Normal Flow
            keyboard = {
                "inline_keyboard": [[{"text": "🔙 Back to Profile", "callback_data": "refresh_profile"}]]
            }
            msg_id = cb["message"]["message_id"]
            from .utils import edit_telegram_message
            edit_telegram_message(chat_id, msg_id, f"✅ Blood Type Updated to <b>{b_type}</b>", reply_markup=keyboard)
            return

        # 2. Set Sex (Finalize)
        if data_str.startswith("set_sex_"):
             # Answer callback
            from .utils import answer_callback_query
            answer_callback_query(cb_id)
            
            sex = data_str.split("_")[2]
            supabase.table("villingili_users").update({"sex": sex}).eq("telegram_id", user_id).execute()
            
            keyboard = {
                "inline_keyboard": [[{"text": "🔙 Back to Profile", "callback_data": "refresh_profile"}]]
            }
            msg_id = cb["message"]["message_id"]
            from .utils import edit_telegram_message
            edit_telegram_message(chat_id, msg_id, f"✅ Sex Updated to <b>{sex}</b>", reply_markup=keyboard)
            return
             
        if data_str.startswith("help_") and False: # Disabled Feature
            request_id = data_str.split("_")[1]
            
            # Check Donor Profile
            if not user.get("blood_type"):
                from .utils import answer_callback_query
                answer_callback_query(cb_id, text="⚠️ You are not a registered donor. Contact admin to get registered.", show_alert=True)
                return

            # Process Help
            try:
                # Get Request
                req_query = supabase.table("villingili_requests").select("*").eq("id", request_id).execute()
                if not req_query.data:
                    from .utils import answer_callback_query
                    answer_callback_query(cb_id, text="⚠️ Request not found or expired.", show_alert=True)
                    return
                
                req = req_query.data[0]
                
                # STRICT BLOOD TYPE MATCH CHECK
                # Donor: user.get("blood_type")
                # Request: req.get("blood_type")
                if user.get("blood_type") != req.get("blood_type"):
                     from .utils import answer_callback_query
                     answer_callback_query(cb_id, text=f"⚠️ You are {user.get('blood_type')}. This request needs {req.get('blood_type')}.", show_alert=True)
                     return

                # If passed, answer now
                from .utils import answer_callback_query
                answer_callback_query(cb_id, "Processing help offer...")

                requester_id = req["requester_id"]
                
                # Exchange Info
                requester_info = supabase.table("villingili_users").select("full_name, phone_number").eq("telegram_id", requester_id).single().execute()
                
                if requester_info.data:
                    r_name = requester_info.data.get("full_name")
                    r_phone = requester_info.data.get("phone_number")
                    d_name = user.get("full_name")
                    d_phone = user.get("phone_number")
                    
                    # To Donor
                    send_telegram_message(user_id, f"✅ Thanks for helping!\nContact Requester: {r_name} - {r_phone}")
                    
                    # To Requester
                    if str(requester_id) != str(user_id):
                        send_telegram_message(requester_id, f"🦸♂️ <a href='tg://user?id={user_id}'>{d_name}</a> offered to help!\nPhone: {d_phone}")
                    else:
                        pass # Don't send notification to self (if testing)
                    
                    # Notify Channel
                    import os
                    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                    if channel_id:
                        send_telegram_message(channel_id, f"🦸♂️ <b>{d_name}</b> offered to help a pending request!")
                    
                    # Update Count
                    new_count = (req.get("donors_found") or 0) + 1
                    supabase.table("villingili_requests").update({"donors_found": new_count}).eq("id", request_id).execute()
            except Exception as e:
                print(f"Help Error: {e}")
                
        if data_str.startswith("edit_field_"):
             from .utils import answer_callback_query, edit_telegram_message
             answer_callback_query(cb_id)
             
             field = data_str.split("_")[2]
             
             if field == "blood":
                 keyboard = {
                    "inline_keyboard": [
                        [{"text": "A+", "callback_data": "set_blood_A+"}, {"text": "A-", "callback_data": "set_blood_A-"}],
                        [{"text": "B+", "callback_data": "set_blood_B+"}, {"text": "B-", "callback_data": "set_blood_B-"}],
                        [{"text": "O+", "callback_data": "set_blood_O+"}, {"text": "O-", "callback_data": "set_blood_O-"}],
                        [{"text": "AB+", "callback_data": "set_blood_AB+"}, {"text": "AB-", "callback_data": "set_blood_AB-"}],
                        [{"text": "🔙 Cancel", "callback_data": "refresh_profile"}]
                    ]
                 }
                 msg_id = cb["message"]["message_id"]
                 edit_telegram_message(chat_id, msg_id, "🩸 <b>Select New Blood Type:</b>", reply_markup=keyboard)
                 
             elif field == "sex":
                 keyboard = {
                    "inline_keyboard": [
                        [{"text": "Male", "callback_data": "set_sex_Male"}, {"text": "Female", "callback_data": "set_sex_Female"}],
                         [{"text": "🔙 Cancel", "callback_data": "refresh_profile"}]
                    ]
                 }
                 msg_id = cb["message"]["message_id"]
                 edit_telegram_message(chat_id, msg_id, "⚧ <b>Select New Sex:</b>", reply_markup=keyboard)
                 
             elif field == "id":
                 msg_id = cb["message"]["message_id"]
                 force_reply = {"force_reply": True, "input_field_placeholder": "A123456"}
                 send_telegram_message(chat_id, "🆔 <b>Reply to this message with your new ID Card Number:</b>", reply_markup=force_reply)
                 # Optional: Answer callback to remove load state, but message stays
                 
             elif field == "address":
                  msg_id = cb["message"]["message_id"]
                  force_reply = {"force_reply": True, "input_field_placeholder": "e.g. Male', Addu..."}
                  send_telegram_message(chat_id, "🏠 <b>Reply to this message with your new Address:</b>", reply_markup=force_reply)

             return

        if data_str == "refresh_profile":
             from .utils import answer_callback_query, edit_telegram_message
             answer_callback_query(cb_id, "Refreshing...")
             
             # Re-fetch user
             user_q = supabase.table("villingili_users").select("*").eq("telegram_id", user_id).execute()
             if user_q.data:
                 u = user_q.data[0]
                 msg_text = (
                     f"👤 <b>Verified Profile</b>\n\n"
                     f"📛 <b>Name:</b> {u.get('full_name')}\n"
                     f"🩸 <b>Blood:</b> {u.get('blood_type') or 'Not Set'}\n"
                     f"⚧ <b>Sex:</b> {u.get('sex') or 'Not Set'}\n"
                     f"🆔 <b>ID Card:</b> {u.get('id_card_number') or 'Not Set'}\n"
                     f"🏠 <b>Address:</b> {u.get('address') or 'Not Set'}\n"
                     f"📱 <b>Phone:</b> {u.get('phone_number')}"
                 )
                 keyboard = {
                     "inline_keyboard": [
                         [{"text": "🩸 Edit Blood Type", "callback_data": "edit_field_blood"}, {"text": "⚧ Edit Sex", "callback_data": "edit_field_sex"}],
                         [{"text": "🆔 Edit ID Card", "callback_data": "edit_field_id"}, {"text": "🏠 Edit Address", "callback_data": "edit_field_address"}],
                         [{"text": "🔄 Refresh", "callback_data": "refresh_profile"}]
                     ]
                 }
                 msg_id = cb["message"]["message_id"]
                 edit_telegram_message(chat_id, msg_id, msg_text, reply_markup=keyboard)
             return
                 
        if data_str.startswith("activate_user_"):
             target_id = data_str.split("_")[2]
             
             # Activate
             supabase.table("villingili_users").update({"status": "active"}).eq("telegram_id", target_id).execute()
             
             # Notify Admin
             from .utils import edit_telegram_message, answer_callback_query
             answer_callback_query(cb_id, "User Activated")
             edit_telegram_message(chat_id, cb["message"]["message_id"], f"✅ <b>User {target_id} has been ACTIVATED.</b>")
             
             # Notify User
             send_telegram_message(target_id, "✅ <b>Your account has been activated!</b>\nYou can now receive requests.")
             return

        if data_str.startswith("cancel_activate_"):
             from .utils import answer_callback_query
             answer_callback_query(cb_id, "Cancelled")
             msg_id = cb["message"]["message_id"]
             edit_telegram_message(chat_id, msg_id, "❌ <b>Activation Request Cancelled.</b>")
             return

        if data_str.startswith("remove_user_"):
             target_id = data_str.split("_")[2]
             
             # Deactivate (Set to pending to satisfy DB constraint)
             supabase.table("villingili_users").update({"status": "pending"}).eq("telegram_id", target_id).execute()
             
             # Notify Admin
             from .utils import edit_telegram_message, answer_callback_query
             answer_callback_query(cb_id, "User Removed")
             edit_telegram_message(chat_id, cb["message"]["message_id"], f"✅ <b>User {target_id} has been deactivated.</b>")
             
             # Notify User
             send_telegram_message(target_id, "🚫 <b>Your account has been deactivated as per your request.</b>\nContact admin to reactivate.")
             return

        if data_str.startswith("cancel_remove_"):
             from .utils import answer_callback_query, delete_telegram_message
             answer_callback_query(cb_id, "Cancelled")
             # Just delete the request message or edit it
             msg_id = cb["message"]["message_id"]
             edit_telegram_message(chat_id, msg_id, "❌ <b>Removal Request Cancelled.</b>")
             return

        return

    # Handle Messages
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        chat_type = msg["chat"]["type"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "")
        contact = msg.get("contact")
        photo = msg.get("photo")

                            


        # ADMIN ACCESS COMMAND (Restricted to Admin Group)
        if text == "/admin_access" or text == "/reset_password":
            import os
            env_grp = os.environ.get("TELEGRAM_ADMIN_GROUP_ID")
            # Default to a dummy if not set to prevent authorized access by mistake, or handle error
            if not env_grp or str(chat_id) != str(env_grp):
                 # Ignore if not in correct group
                 return

            target_id = user_id
            target_name = msg.get("from", {}).get("first_name", "User")
            target_user = msg.get("from", {}).get("username", target_name)
            
            # Check reply
            reply = msg.get("reply_to_message")
            if reply:
                 target_id = reply['from']['id']
                 target_name = reply['from']['first_name']
                 target_user = reply['from'].get('username', target_name)
            
            # Generate Password
            import secrets
            new_pass = secrets.token_urlsafe(6)
            
            # Fetch Phone Number Schema
            phone_val = "Linked"
            target_username = target_user 

            try:
                import time
                # Fetch real phone from users table
                existing_u = supabase.table("villingili_users").select("phone_number").eq("telegram_id", target_id).execute()
                if existing_u.data and existing_u.data[0].get('phone_number'):
                     p = existing_u.data[0]['phone_number']
                     if not str(p).startswith("pending"):
                         phone_val = p
                         target_username = p 

                # Upsert to Admin Table
                admin_data = {
                    "telegram_id": target_id,
                    "username": target_username,
                    "password": new_pass,
                    "phone_number": phone_val
                }
                
                supabase.table("villingili_admin_users").upsert(admin_data, on_conflict="telegram_id").execute()
                
                # PM The user
                msg_out = (
                    f"🔐 <b>Admin Dashboard Access</b>\n\n"
                    f"👤 User: <code>{target_username}</code>\n"
                    f"🔑 Pass: <code>{new_pass}</code>\n\n"
                    f"Use these to login at the dashboard."
                )
                sent = send_telegram_message(target_id, msg_out)
                if sent and sent.get("ok"):
                     send_telegram_message(chat_id, f"✅ Credentials sent to {target_name} via PM.")
                else:
                     send_telegram_message(chat_id, f"⚠️ Couldn't PM {target_name}. Please start the bot first!")
            except Exception as e:
                print(f"Admin Access Error: {e}")
                send_telegram_message(chat_id, "⚠️ Error creating admin credentials.")
            return
        # LOGIC FOR GROUPS/SUPERGROUPS (Early Check for Photos)
        if chat_type in ["group", "supergroup"]:
            # Load from Env (Fallback to previous hardcoded if missing)
            import os
            env_grp = os.environ.get("TELEGRAM_ADMIN_GROUP_ID")
            ADMIN_GROUP_ID = int(env_grp) if env_grp else -1003695872031
            
            print(f"DEBUG: Checking Group Message. Chat ID: {chat_id}, Configured Admin Group: {ADMIN_GROUP_ID}", flush=True)

            # Debug Mismatch (For troubleshooting ONLY)
            if int(chat_id) != ADMIN_GROUP_ID and photo:
                 send_telegram_message(chat_id, f"⚠️ **Debug:** Wrong Group ID.\nThis Group: `{chat_id}`\nConfigured: `{ADMIN_GROUP_ID}`")
                 return



            # 1. HANDLE PHOTOS (ID Card Scan)
            if int(chat_id) == ADMIN_GROUP_ID and photo:
                try:
                    # Get largest photo
                    file_id = photo[-1]["file_id"]
                    
                    # Get File Path
                    import requests
                    import os
                    token = os.environ.get("TELEGRAM_BOT_TOKEN")
                    res = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}").json()
                    
                    if res.get("ok"):
                        file_path = res["result"]["file_path"]
                        image_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                        
                        send_telegram_message(chat_id, "🔍 Scanning ID Card...")
                        
                        # Analyze
                        from .utils import analyze_id_card_with_ai
                        result = analyze_id_card_with_ai(image_url)
                        
                        if result:
                            # 1. Invalid Image Handling
                            if not result.get("is_valid"):
                                error_code = result.get("error")
                                if error_code == "UNCLEAR":
                                    send_telegram_message(chat_id, "⚠️ **Image Unclear**\nPlease re-upload a **clear image** of the ID card without glare or reflection.")
                                else:
                                    send_telegram_message(chat_id, "❌ **Not Identified**\nPlease upload a valid Maldives National Identity Card.")
                                return

                            # 2. Success - Extract & Ask for Blood Type
                            name = result.get("full_name", "Unknown")
                            nid = result.get("id_card_number", "Unknown")
                            sex = result.get("sex", "Unknown")
                            addr = result.get("address", "Unknown")
                            dob = result.get("date_of_birth", "Unknown")
                            
                            # Normalize Sex
                            if sex and sex.upper().startswith("M"): sex = "Male"
                            elif sex and sex.upper().startswith("F"): sex = "Female"

                            # Store temporarily using a callback-friendly approach or DB draft
                            # Since callback data is limited (64 bytes), we can't put everything there.
                            # We will upsert a 'draft' user into DB with status='draft_scanning'
                            
                            # Generate Temp ID from NID hash to be consistent
                            import hashlib
                            id_hash = int(hashlib.sha256(nid.encode('utf-8')).hexdigest(), 16) % (10**12)
                            fake_tg_id = id_hash 
                            
                            # Store in DB as DRAFT
                            user_data = {
                                "telegram_id": fake_tg_id,
                                "full_name": name,
                                "phone_number": f"DRAFT_{fake_tg_id}", # Placeholder to satisfy NOT NULL constraint
                                "id_card_number": nid,
                                "sex": sex,
                                "address": addr,
                                "status": "pending", # Satisfies CHECK (status in ('active', 'pending', 'banned'))
                                "role": "user"
                            }
                            # Upsert by ID Card Number to handle re-uploads/corrections
                            # But we need to be careful not to overwrite valid active users if we are just "checking"
                            # The requirement is to 'update db', so upserting IS the goal.
                            # We'll use 'id_card_number' as the unique key for this logic basically.
                            
                            # Manual Upsert (Check -> Insert/Update)
                            try:
                                ex = supabase.table("villingili_users").select("telegram_id").eq("telegram_id", fake_tg_id).execute()
                                if ex.data:
                                    supabase.table("villingili_users").update(user_data).eq("telegram_id", fake_tg_id).execute()
                                else:
                                    supabase.table("villingili_users").insert(user_data).execute()
                            except Exception as e:
                                print(f"DB Upsert Error: {e}")
                                send_telegram_message(chat_id, f"⚠️ Database Error: {e}")
                                return
                            
                            # Send Blood Type Buttons
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "A+", "callback_data": f"admin_set_blood_{fake_tg_id}_A+"}, {"text": "A-", "callback_data": f"admin_set_blood_{fake_tg_id}_A-"}],
                                    [{"text": "B+", "callback_data": f"admin_set_blood_{fake_tg_id}_B+"}, {"text": "B-", "callback_data": f"admin_set_blood_{fake_tg_id}_B-"}],
                                    [{"text": "O+", "callback_data": f"admin_set_blood_{fake_tg_id}_O+"}, {"text": "O-", "callback_data": f"admin_set_blood_{fake_tg_id}_O-"}],
                                    [{"text": "AB+", "callback_data": f"admin_set_blood_{fake_tg_id}_AB+"}, {"text": "AB-", "callback_data": f"admin_set_blood_{fake_tg_id}_AB-"}]
                                ]
                            }
                            
                            msg = (
                                f"✅ **ID Scanned Successfully!**\n\n"
                                f"👤 Name: {name}\n"
                                f"🆔 ID: {nid}\n"
                                f"🎂 DOB: {dob}\n"
                                f"🏠 Addr: {addr}\n\n"
                                f"🩸 **Select Blood Type:**"
                            )
                            send_telegram_message(chat_id, msg, reply_markup=keyboard)
                        else:
                             send_telegram_message(chat_id, "⚠️ AI Analysis failed. Please try again.")


                    
                    return # Stop processing
                    
                except Exception as e:
                    print(f"Photo Error: {e}")
                    send_telegram_message(chat_id, f"⚠️ Error processing photo: {e}")
                    return
                    return
        
            # 2. Handle ID Card Phone Input (Admin Group)
            reply = msg.get("reply_to_message")
            # DEBUG LOGGING (Temporary)
            if reply:
                 print(f"DEBUG: Reply detected in Chat {chat_id}. Text: {reply.get('text', '')[:20]}...")
            if int(chat_id) == ADMIN_GROUP_ID and reply and "REF:" in reply.get("text", ""):
                 print("DEBUG: REF ID found in reply. Processing...")
                 ref_line = [l for l in reply.get("text", "").split("\n") if "REF:" in l]
                 if ref_line:
                     fake_id_str = ref_line[0].split("REF:")[1].strip()
                     # Validate Phone (Maldives Mobile: 7xxxxxx or 9xxxxxx)
                     raw_ph = text.strip()
                     import re
                     digits = re.sub(r"\D", "", raw_ph)
                     
                     final_phone = None
                     if len(digits) == 7 and digits[0] in ['7', '9']:
                         final_phone = digits # Store 7 digits
                     elif len(digits) == 10 and digits.startswith("960") and digits[3] in ['7', '9']:
                         final_phone = digits[3:] # Strip 960, store 7 digits
                         
                     if final_phone:
                         # ROBUST MERGE LOGIC (Patch V3)
                         try:
                             # Check if Phone Exists
                             existing_ph = supabase.table("villingili_users").select("*").eq("phone_number", final_phone).execute()
                             if existing_ph.data:
                                 conflict_user = existing_ph.data[0]
                                 # Merge New Info (Scan) INTO Old User (Mobile)
                                 c_pk = conflict_user["telegram_id"]
                                 # Get Target Info (Scan User)
                                 try:
                                     target_u_res = supabase.table("villingili_users").select("*").eq("telegram_id", fake_id_str).execute()
                                 except Exception as e:
                                     return
                                     
                                 if target_u_res.data:
                                      target_u = target_u_res.data[0]
                                      # Update Conflict User with ID Details
                                      supabase.table("villingili_users").update({
                                           "full_name": target_u.get("full_name"),
                                           "id_card_number": target_u.get("id_card_number"),
                                           "sex": target_u.get("sex"),
                                           "address": target_u.get("address"),
                                           "blood_type": target_u.get("blood_type"),
                                           "status": "active"
                                      }).eq("telegram_id", c_pk).execute()
                                      # Delete Pending Scan User
                                      supabase.table("villingili_users").delete().eq("telegram_id", fake_id_str).execute()
                                      send_telegram_message(chat_id, f"✅ <b>Merged!</b>\nPhone {final_phone} was already registered.\nUpdated record with ID Card info.")
                                      # Notify User
                                      try:
                                          kb = {"keyboard": [[{"text": "🩸 Request Blood"}]], "resize_keyboard": True}
                                          send_telegram_message(c_pk, "✅ <b>Your Profile has been Updated!</b>\nYou can now request blood.", reply_markup=kb)
                                      except: pass
                                 else:
                                      send_telegram_message(chat_id, "⚠️ Error finding pending scan record.")
                             else:
                                 # Normal Update
                                 supabase.table("villingili_users").update({
                                     "phone_number": final_phone,
                                     "status": "active"
                                 }).eq("telegram_id", fake_id_str).execute()
                                 send_telegram_message(chat_id, f"✅ <b>Registration Complete!</b>\nPhone: {final_phone}\n\nUser is now active.")
                         except Exception as e:
                             err_str = str(e)
                             if "23505" in err_str or "already exists" in err_str:
                                 # FORCE MERGE (Duplicate Key)
                                 try:
                                     # Fetch the Conflict User
                                     con_res = supabase.table("villingili_users").select("*").eq("phone_number", final_phone).execute()
                                     if con_res.data:
                                          conflict_user = con_res.data[0]
                                          c_pk = conflict_user["telegram_id"]
                                          # Update Conflict User
                                          supabase.table("villingili_users").update({
                                               "full_name": target_u.get("full_name"),
                                               "id_card_number": target_u.get("id_card_number"),
                                               "sex": target_u.get("sex"),
                                               "address": target_u.get("address"),
                                               "blood_type": target_u.get("blood_type"),
                                               "status": "active"
                                          }).eq("telegram_id", c_pk).execute()
                                          # Delete Draft
                                          supabase.table("villingili_users").delete().eq("telegram_id", fake_id_str).execute()
                                          send_telegram_message(chat_id, f"✅ <b>Merged!</b>\nPhone {final_phone} was already registered.\nUpdated record with ID Card info.")
                                          return
                                 except Exception as merge_err:
                                      print(f"Merge Error: {merge_err}")
                                      send_telegram_message(chat_id, f"⚠️ Error merging: {merge_err}")
                             else:
                                 send_telegram_message(chat_id, f"⚠️ Error updating phone: {e}")
                     else:
                         send_telegram_message(chat_id, "⚠️ Invalid Mobile Number.\nMust be a local mobile number starting with <b>7</b> or <b>9</b> (e.g., 7771234).")
                     return

            # 3. Handle Blood Group Search (Admin Group Text)
            if int(chat_id) == ADMIN_GROUP_ID and text and not text.startswith("/"):
                 # A. Explicit "list" command
                 if text.strip().lower() == "list":
                      donors = supabase.table("villingili_users").select("full_name, phone_number, blood_type").neq("blood_type", None).execute()
                      if donors.data:
                           # Group by Blood Type
                           grouped = {}
                           for d in donors.data:
                                bt = d.get('blood_type') or "Unknown"
                                if bt not in grouped: grouped[bt] = []
                                grouped[bt].append(d)
                           
                           # Build Message
                           msg_list = ["<b>📋 Donor List:</b>"]
                           for bt in sorted(grouped.keys()):
                                msg_list.append(f"\n<b>{bt}</b>")
                                for d in grouped[bt]:
                                     msg_list.append(f"- {d['full_name']}: {d['phone_number']}")
                           
                           full_msg = "\n".join(msg_list)
                           # Simple split if too long (naive)
                           if len(full_msg) > 4000:
                                send_telegram_message(chat_id, full_msg[:4000] + "...")
                                send_telegram_message(chat_id, "..." + full_msg[4000:])
                           else:
                                send_telegram_message(chat_id, full_msg)
                      else:
                           send_telegram_message(chat_id, "No donors found with blood type set.")
                      return

                 # B. Specific Blood Type Search (Short text)
                 if len(text) < 5:
                     bt = text.strip().upper()
                     valid_types = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                     if bt in valid_types:
                          donors = supabase.table("villingili_users").select("full_name, phone_number").eq("blood_type", bt).execute()
                          if donors.data:
                              msg = f"<b>Donors for {bt}:</b>\n"
                              for d in donors.data:
                                   msg += f"- {d['full_name']}: {d['phone_number']}\n"
                              send_telegram_message(chat_id, msg)
                          else:
                              send_telegram_message(chat_id, f"No donors found for {bt}.")
                          return

                          return

                 # C. Help Command
                 if text.strip().lower() == "help":
                      help_msg = (
                          "<b>🛠 Admin Group Commands:</b>\n"
                          "1. <b>list</b> - Show ALL active donors (grouped by blood type).\n"
                          "2. <b>[Type]</b> (e.g. <code>A+</code>) - Show donors for that type.\n"
                          "3. <b>[Photo]</b> - Send ID Card Photo to scan/register.\n"
                          "4. <b>Reply to Scan</b> - Reply with Phone Number to link/merge.\n"
                          "5. <b>/admin_access</b> or <b>/reset_password</b>"
                      )
                      send_telegram_message(chat_id, help_msg)
                      return

        if text and text.startswith("/start"):
            args = text.split()
            if len(args) > 1:
                payload = args[1]
                if payload.startswith("help_"):
                    req_id = payload.split("_")[1]
                    try:
                        # If user exists, just save intent
                        if user_exists:
                             supabase.table("villingili_users").update({"pending_request_id": req_id}).eq("telegram_id", user_id).execute()
                             send_telegram_message(user_id, "ℹ️ You selected a request to help.\nPlease share your contact to proceed.")
                        else:
                             # New User: Create Pending Stub to preserve ID
                             pseudo_phone = f"pending_{user_id}"
                             stub_data = {
                                 "telegram_id": user_id,
                                 "full_name": msg["chat"].get("first_name", "Pending User"),
                                 "phone_number": pseudo_phone,
                                 "status": "pending",
                                 "pending_request_id": req_id,
                                 "role": "user"
                             }
                             supabase.table("villingili_users").upsert(stub_data).execute()
                             # Note: Next time this user messages, they will be found as 'pending'
                    except Exception as e:
                        print(f"Start Payload Error: {e}")

        # 1. Check if user is registered (using user_id, NOT chat_id)
        try:
             user_query = supabase.table("villingili_users").select("*").eq("telegram_id", user_id).execute()
             user = user_query.data[0] if user_query.data else None
             user_exists = user is not None
        except Exception as e:
            print(f"DB Error: {e}")
            return
            
        if chat_type == "private":
            # 2. Lazy Registration Flow (New OR Pending Users)
            if not user_exists or (user and user.get("status") == "pending"):
                if contact:
                    # User sent contact - Register them
                    try:
                        raw_phone = contact["phone_number"]
                        # Remove Maldives country code if present
                        if raw_phone.startswith("960"):
                            phone = raw_phone[3:]
                        elif raw_phone.startswith("+960"):
                            phone = raw_phone[4:]
                        else:
                            phone = raw_phone

                        user_data = {
                            "telegram_id": user_id,
                            "phone_number": phone,
                            "full_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                            "username": msg["chat"].get("username"),
                            "status": "active"
                        }

                        # Check for phone conflict (Same phone, different ID)
                        existing_phone = supabase.table("villingili_users").select("telegram_id").eq("phone_number", phone).neq("telegram_id", user_id).execute()
                        
                        if existing_phone.data:
                             old_id = existing_phone.data[0]['telegram_id']
                             print(f"Migrating user {old_id} to {user_id}...")
                             
                             # 1. Free up the phone number (change old to temporary)
                             supabase.table("villingili_users").update({"phone_number": f"{phone}_old_{old_id}"}).eq("telegram_id", old_id).execute()
                             
                             # 2. Register New User
                             supabase.table("villingili_users").upsert(user_data).execute()
                             
                             # 3. Migrate Requests (Move ownership)
                             supabase.table("villingili_requests").update({"requester_id": user_id}).eq("requester_id", old_id).execute()
                             
                             # 4. Delete Old User
                             supabase.table("villingili_users").delete().eq("telegram_id", old_id).execute()
                        else:
                             # Normal Upsert
                             supabase.table("villingili_users").upsert(user_data).execute()
                        

                        

                        
                        # Check for deferred help (from stub or update)
                        # We use 'pending_req' from the OLD user object (if it existed) OR we refetch?
                        # Since we just upserted user_data (which doesn't have pending_request_id),
                        # the pending_ID is RESERVED in the DB if we used upsert properly on existing row?
                        # Yes, upsert only updates provided columns unless specified? 
                        # Wait, Supabase upsert replaces pending_request_id with NULL if not provided?
                        # NO. It only updates columns in the JSON unless it's a full replace.
                        # Actually standard SQL UPDATE/INSERT... 
                        # BUT we used `upsert`. 
                        
                        # CRITICAL: We might have WIPED the pending_request_id if we didn't include it.
                        # Let's hope not. To be safe, let's use the one from `user` object we fetched at start of loop (line 448).
                        # If user was 'pending' status, `user` object has the `pending_request_id`.
                        
                        pending_req = user.get("pending_request_id") if user else None
                        
                        if pending_req:
                            send_telegram_message(chat_id, "🔄 Processing your help offer...")
                            try:
                                user_data["pending_request_id"] = pending_req 
                                
                                # 1. Check Profile (Blood Type) - New Phase: Require Blood Type
                                if not user_data.get("blood_type"): 
                                     send_telegram_message(user_id, "⚠️ To help, please complete your profile details first:")
                                     from .utils import check_and_prompt_missing_info
                                     check_and_prompt_missing_info(user_id, user_data)
                                     return

                                # 2. Process Help
                                req_query = supabase.table("villingili_requests").select("*").eq("id", pending_req).execute()
                                if req_query.data:
                                    req = req_query.data[0]
                                    requester_id = req["requester_id"]
                                    requester_info = supabase.table("villingili_users").select("full_name, phone_number").eq("telegram_id", requester_id).single().execute()
                                    
                                    if requester_info.data:
                                        r_name = requester_info.data.get("full_name")
                                        r_phone = requester_info.data.get("phone_number")
                                        d_name = user_data.get("full_name")
                                        d_phone = user_data.get("phone_number")
                                        
                                        send_telegram_message(user_id, f"✅ Thanks for helping!\nContact Requester: {r_name} - {r_phone}")
                                        if str(requester_id) != str(user_id):
                                            send_telegram_message(requester_id, f"🦸♂️ <a href='tg://user?id={user_id}'>{d_name}</a> offered to help!\nPhone: {d_phone}")
                                        
                                        import os
                                        channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                                        if channel_id:
                                            send_telegram_message(channel_id, f"🦸♂️ <b>{d_name}</b> offered to help a pending request!")
                                        
                                        new_count = (req.get("donors_found") or 0) + 1
                                        supabase.table("villingili_requests").update({"donors_found": new_count}).eq("id", pending_req).execute()
                                        supabase.table("villingili_users").update({"pending_request_id": None}).eq("telegram_id", user_id).execute()
                                        return
                            except Exception as e:
                                 print(f"Deferred Help Error: {e}")

                        # Standard Flow (Request First) if no help processed
                        # Wait for client to process keyboard removal
                        await asyncio.sleep(1)

                        # Set Persistent Keyboard via Welcome Message
                        persistent_kb = {
                            "keyboard": [[{"text": "👋 Welcome Back!"}]],
                            "resize_keyboard": True
                        }
                        send_telegram_message(chat_id, "👋 <b>Welcome!</b>", reply_markup=persistent_kb)

                        # New Logic: Assume Seeker first
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "A+", "callback_data": "req_blood_A+"}, {"text": "A-", "callback_data": "req_blood_A-"}],
                                [{"text": "B+", "callback_data": "req_blood_B+"}, {"text": "B-", "callback_data": "req_blood_B-"}],
                                [{"text": "O+", "callback_data": "req_blood_O+"}, {"text": "O-", "callback_data": "req_blood_O-"}],
                                [{"text": "AB+", "callback_data": "req_blood_AB+"}, {"text": "AB-", "callback_data": "req_blood_AB-"}]
                            ]
                        }
                        send_telegram_message(chat_id, "🩸 <b>Select blood group you want:</b>", reply_markup=keyboard)
                        
                    except Exception as e:
                        print(f"Registration Error: {e}")
                        send_telegram_message(chat_id, "⚠️ Error registering. Please try again.")
                else:
                    # Prompt for Contact
                    keyboard = {
                        "keyboard": [[{"text": "✅ START", "request_contact": True}]],
                        "resize_keyboard": True,
                        "one_time_keyboard": True
                    }
                    send_telegram_message(chat_id, "👋 Welcome to Blood Donation-Siwad.\n\nPlease click the **START** button below to proceed.\n\n👇👇👇\n\n<i>Don't see the button?</i>\nClick the 🎛 <b>Menu/Keyboard Icon</b> in your text bar to reveal it.", reply_markup=keyboard)
            


            # 3. Registered User Flow (Private)
            else:
                # Check BANNED status
                if user.get("status") == "banned":
                    send_telegram_message(chat_id, "🚫 <b>Access Denied</b>\nYour account has been banned.Contact Admin for more info.")
                    return

                # Check for Replied Messages (ID Card / Address)
                reply = msg.get("reply_to_message")
                # Handle PROFILE UPDATE replies
                # ADMIN COMMANDS (Group Only)

                # Normal User Flow (Private Chat Checks)
                if chat_type == "private":
                     if reply:
                          r_text = reply.get("text", "")
                    
                    # Handle REQUEST CREATION reply
                          if "Requesting" in r_text and "Location" in r_text:
                              # Extract blood type from "Requesting B+..."
                              # Format: "🏥 Requesting <b>B+</b>..."
                              try:
                                  import re
                                  match = re.search(r"Requesting\s+(.*?)\.", r_text) # Simple regex or plain split
                                  # actually HTML might be stripped in 'text' field of reply_to_message? 
                                  # usually 'text' has raw text. "Requesting B+."
                                  # Let's trust the bold markers might be gone or present.
                            
                                  # Fallback parsing
                                  blood_type = "Unknown"
                                  if "A+" in r_text: blood_type = "A+"
                                  elif "A-" in r_text: blood_type = "A-"
                                  elif "B+" in r_text: blood_type = "B+"
                                  elif "B-" in r_text: blood_type = "B-"
                                  elif "O+" in r_text: blood_type = "O+"
                                  elif "O-" in r_text: blood_type = "O-"
                                  elif "AB+" in r_text: blood_type = "AB+"
                                  elif "AB-" in r_text: blood_type = "AB-"
                            
                                  location = text
                                  urgency = "Normal" # Default
                            
                                  # VALIDATION
                                  valid_types = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                                  if blood_type not in valid_types:
                                       send_telegram_message(chat_id, "⚠️ <b>Incomplete Blood Type</b>\nPlease specify if Positive (+) or Negative (-).")
                                       return

                                  # create request
                                  req_data = {
                                       "requester_id": user_id,
                                       "blood_type": blood_type,
                                       "location": location,
                                       "urgency": urgency,
                                       "is_active": True
                                  }
                                  res = supabase.table("villingili_requests").insert(req_data).execute()
                                  req_id = res.data[0]['id']
                            
                                  # Broadcast to Channel
                                  channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                                  if channel_id:
                                       from .utils import format_blood_request_message
                                       msg_text = format_blood_request_message(blood_type, location, urgency, user['full_name'], user.get('phone_number'))
                                       keyboard = {
                                            "inline_keyboard": [[
                                                {"text": "🙋♂️ I Can Help", "callback_data": f"help_{req_id}"}
                                            ]]
                                       }
                                       sent = send_telegram_message(channel_id, msg_text)
                                       if sent and sent.get("ok"):
                                          msg_id = sent["result"]["message_id"]
                                          supabase.table("villingili_requests").update({"telegram_message_id": msg_id}).eq("id", req_id).execute()

                                  send_telegram_message(chat_id, f"✅ <b>Request Sent!</b>\n\nWe have broadcast your need for <b>{blood_type}</b> at <b>{location}</b> to the channel.")
                            
                                  # Now ask if they want to register as donor?
                                  # Maybe not now, don't spam.
                                  return

                              except Exception as e:
                                  print(f"Request Creation Error: {e}")
                                  send_telegram_message(chat_id, "⚠️ Error creating request.")
                                  return

                          if "Mobile Number" in r_text:
                              phone = text.strip()
                              # Basic validation
                              if not phone.isdigit() or len(phone) < 7:
                                   send_telegram_message(chat_id, "⚠️ Invalid format. Please send 7 digits.")
                                   return

                              # Check conflict
                              # Check conflict (Robust Logic via Patch)
                              existing_res = supabase.table("villingili_users").select("*").eq("phone_number", phone).execute()
                              conflict_user = next((u for u in existing_res.data if str(u.get("telegram_id")) != str(chat_id)), None)

                              if conflict_user:
                                  import time
                                  c_pk = conflict_user["telegram_id"]
                                  old_tg_id = conflict_user.get("telegram_id")
                                  send_telegram_message(chat_id, f"🔄 Found existing record for **{conflict_user.get('full_name', 'User')}**. Merging...")
                                  temp_phone = f"{phone}_old_{int(time.time())}"
                                  supabase.table("villingili_users").update({"phone_number": temp_phone}).eq("telegram_id", c_pk).execute()
                                  supabase.table("villingili_users").update({"phone_number": phone}).eq("telegram_id", chat_id).execute()
                                  user["phone_number"] = phone
                                  updates = {}
                                  for field in ["sex", "address", "island", "birth_date", "blood_type", "permanent_address"]:
                                       if not user.get(field) and conflict_user.get(field):
                                           updates[field] = conflict_user[field]
                                  if updates:
                                       supabase.table("villingili_users").update(updates).eq("telegram_id", chat_id).execute()
                                       user.update(updates)
                                  if old_tg_id:
                                       supabase.table("villingili_requests").update({"requester_id": chat_id}).eq("requester_id", old_tg_id).execute()
                                  supabase.table("villingili_users").delete().eq("id", c_pk).execute()
                                  send_telegram_message(chat_id, "✅ Account merged successfully!")
                              else:
                                  supabase.table("villingili_users").update({"phone_number": phone}).eq("telegram_id", chat_id).execute()
                                  user["phone_number"] = phone

                              from .utils import check_and_prompt_missing_info
                              check_and_prompt_missing_info(chat_id, user)
                              return

                          if "ID Card Number" in r_text:
                              supabase.table("users").update({"id_card_number": text}).eq("telegram_id", chat_id).execute()
                              user['id_card_number'] = text # Update local user obj
                              from .utils import check_and_prompt_missing_info
                              check_and_prompt_missing_info(chat_id, user)
                              return
                    
                          if "Address" in r_text:
                              supabase.table("users").update({"address": text}).eq("telegram_id", chat_id).execute()
                              user['address'] = text
                              from .utils import check_and_prompt_missing_info
                              check_and_prompt_missing_info(chat_id, user)
                              return

                if text == "👋 Welcome Back!" or text == "🩸 Request Blood": # Support both for migration or just matches new text
                     # JUST Show Inline Menu (No extra message)
                     keyboard = {
                          "inline_keyboard": [
                               [{"text": "A+", "callback_data": "req_blood_A+"}, {"text": "A-", "callback_data": "req_blood_A-"}],
                               [{"text": "B+", "callback_data": "req_blood_B+"}, {"text": "B-", "callback_data": "req_blood_B-"}],
                               [{"text": "O+", "callback_data": "req_blood_O+"}, {"text": "O-", "callback_data": "req_blood_O-"}],
                               [{"text": "AB+", "callback_data": "req_blood_AB+"}, {"text": "AB-", "callback_data": "req_blood_AB-"}]
                          ]
                     }
                     send_telegram_message(chat_id, "🩸 <b>Please select a blood group to request:</b>", reply_markup=keyboard)
                     return # Important loop break

                elif contact:
                     # Already registered but shared contact again
                     # Ensure persistent button + show menu
                     persistent_kb = {
                         "keyboard": [[{"text": "👋 Welcome Back!"}]],
                         "resize_keyboard": True
                     }
                     send_telegram_message(chat_id, "🔍 <b>Menu Refreshed</b>", reply_markup=persistent_kb)

                     keyboard = {
                          "inline_keyboard": [
                               [{"text": "A+", "callback_data": "req_blood_A+"}, {"text": "A-", "callback_data": "req_blood_A-"}],
                               [{"text": "B+", "callback_data": "req_blood_B+"}, {"text": "B-", "callback_data": "req_blood_B-"}],
                               [{"text": "O+", "callback_data": "req_blood_O+"}, {"text": "O-", "callback_data": "req_blood_O-"}],
                               [{"text": "AB+", "callback_data": "req_blood_AB+"}, {"text": "AB-", "callback_data": "req_blood_AB-"}]
                          ]
                     }
                     send_telegram_message(chat_id, "🩸 <b>Please select a blood group to request:</b>", reply_markup=keyboard)
                
                elif text == "/start":
                     # Same logic as above for consistency
                     persistent_kb = {
                         "keyboard": [[{"text": "👋 Welcome Back!"}]],
                         "resize_keyboard": True
                     }
                     send_telegram_message(chat_id, "👋 <b>Welcome back!</b>", reply_markup=persistent_kb)

                     keyboard = {
                          "inline_keyboard": [
                               [{"text": "A+", "callback_data": "req_blood_A+"}, {"text": "A-", "callback_data": "req_blood_A-"}],
                               [{"text": "B+", "callback_data": "req_blood_B+"}, {"text": "B-", "callback_data": "req_blood_B-"}],
                               [{"text": "O+", "callback_data": "req_blood_O+"}, {"text": "O-", "callback_data": "req_blood_O-"}],
                               [{"text": "AB+", "callback_data": "req_blood_AB+"}, {"text": "AB-", "callback_data": "req_blood_AB-"}]
                          ]
                     }
                     send_telegram_message(chat_id, "🩸 <b>Select blood group you want:</b>", reply_markup=keyboard)

                elif "remove me" in text.lower() or "delete me" in text.lower():
                     # Send Removal Request to Admin Group
                     import os
                     admin_group = int(os.environ.get("TELEGRAM_ADMIN_GROUP_ID") or -1003695872031)
                     msg_text = (
                         f"⚠️ <b>User Requesting Removal</b>\n\n"
                         f"👤 <b>Username/Name:</b> {user.get('full_name')} (@{msg.get('from', {}).get('username', 'N/A')})\n"
                         f"📱 <b>Phone:</b> {user.get('phone_number')}\n"
                         f"🆔 <b>ID:</b> {user.get('telegram_id')}"
                     )
                     keyboard = {
                         "inline_keyboard": [[
                             {"text": "❌ Remove User", "callback_data": f"remove_user_{chat_id}"},
                             {"text": "🔙 Cancel", "callback_data": f"cancel_remove_{chat_id}"}
                         ]]
                     }
                     send_telegram_message(admin_group, msg_text, reply_markup=keyboard)
                     send_telegram_message(chat_id, "✅ <b>Removal Request Sent.</b>\nAn admin will review and remove you shortly.")

                elif "activate me" in text.lower() or "enable me" in text.lower():
                     # Send Activation Request to Admin Group
                     import os
                     admin_group = int(os.environ.get("TELEGRAM_ADMIN_GROUP_ID") or -1003695872031)
                     msg_text = (
                         f"🟢 <b>User Requesting Activation</b>\n\n"
                         f"👤 <b>Username/Name:</b> {user.get('full_name')} (@{msg.get('from', {}).get('username', 'N/A')})\n"
                         f"📱 <b>Phone:</b> {user.get('phone_number')}\n"
                         f"🆔 <b>ID:</b> {user.get('telegram_id')}"
                     )
                     keyboard = {
                         "inline_keyboard": [[
                             {"text": "✅ Activate User", "callback_data": f"activate_user_{chat_id}"},
                             {"text": "🔙 Cancel", "callback_data": f"cancel_activate_{chat_id}"}
                         ]]
                     }
                     send_telegram_message(admin_group, msg_text, reply_markup=keyboard)
                     send_telegram_message(chat_id, "✅ <b>Activation Request Sent.</b>\nAn admin will review and activate you shortly.")

                elif text == "/donor":
                     from .utils import check_and_prompt_missing_info
                     check_and_prompt_missing_info(chat_id, user)

                elif text == "/update" or text.startswith("/profile"):
                     # Display Profile Dashboard with Edit Buttons
                     msg_text = (
                         f"👤 <b>Verified Profile</b>\n\n"
                         f"📛 <b>Name:</b> {user.get('full_name')}\n"
                         f"🩸 <b>Blood Type:</b> {user.get('blood_type') or 'Not Set'}\n"
                         f"⚧ <b>Sex:</b> {user.get('sex') or 'Not Set'}\n"
                         f"🆔 <b>ID Card:</b> {user.get('id_card_number') or 'Not Set'}\n"
                         f"🏠 <b>Address:</b> {user.get('address') or 'Not Set'}\n"
                         f"📱 <b>Phone:</b> {user.get('phone_number')}"
                     )
                     keyboard = {
                         "inline_keyboard": [
                             [{"text": "🩸 Edit Blood Type", "callback_data": "edit_field_blood"}, {"text": "⚧ Edit Sex", "callback_data": "edit_field_sex"}],
                             [{"text": "🆔 Edit ID Card", "callback_data": "edit_field_id"}, {"text": "🏠 Edit Address", "callback_data": "edit_field_address"}],
                             [{"text": "🔄 Refresh", "callback_data": "refresh_profile"}]
                         ]
                     }
                     send_telegram_message(chat_id, msg_text, reply_markup=keyboard)

                elif text:
 
                    # Check for Blood Request intent
                    if not text.startswith("/"):
                        parsed = parse_request_with_ai(text)
                        if parsed and parsed.get("blood_type"):
                             blood_type = parsed['blood_type']
                             location = parsed.get('location', 'Unknown')
                             urgency = parsed.get('urgency', 'Normal')
                             
                             # VALIDATION
                             valid_types = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                             if blood_type not in valid_types:
                                  send_telegram_message(chat_id, "⚠️ <b>Incomplete Blood Type</b>\nPlease specify if Positive (+) or Negative (-) (e.g., 'A+' or 'A Negative').")
                                  return

                             # Save Request
                             req_data = {
                                 "requester_id": user_id,
                                 "blood_type": blood_type,
                                 "location": location,
                                 "urgency": urgency,
                                 "is_active": True
                             }
                             res = supabase.table("villingili_requests").insert(req_data).execute()
                             req_id = res.data[0]['id']
                             
                             # Broadcast to Channel
                             import os
                             channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
                             if channel_id:
                                 msg_text = (
                                     f"🚨 <b>BLOOD REQUEST</b>\n"
                                     f"Type: {blood_type}\n"
                                     f"Location: {location}\n"
                                     f"Urgency: {urgency}\n"
                                     f"Requester: {user['full_name']}\n"
                                 )
                                 keyboard = {
                                     "inline_keyboard": [[
                                         {"text": "🙋♂️ I Can Help", "callback_data": f"help_{req_id}"}
                                     ]]
                                 }
                                 sent = send_telegram_message(channel_id, msg_text, reply_markup=keyboard)
                                 if sent and sent.get("ok"):
                                     msg_id = sent["result"]["message_id"]
                                     supabase.table("villingili_requests").update({"telegram_message_id": msg_id}).eq("id", req_id).execute()
                             
                             send_telegram_message(chat_id, f"✅ Request sent to channel! Waiting for donors...")
                             
                             # Find Matches
                             try:
                                 donors = supabase.table("villingili_users").select("full_name, phone_number")\
                                     .eq("blood_type", blood_type)\
                                     .neq("telegram_id", chat_id)\
                                     .execute()
                                     
                                 if donors.data:
                                     match_msg = f"🔍 <b>{len(donors.data)} Possible Donors Found:</b>\n"
                                     for d in donors.data:
                                         # User Request: Blood Group | Name | Phone
                                         match_msg += f"- {blood_type} | {d['full_name']} | {d['phone_number']}\n"
                                     send_telegram_message(chat_id, match_msg)
                                 else:
                                     send_telegram_message(chat_id, f"⚠️ <b>No direct matches found.</b>\nWe have broadcast your request to the channel.")
                             except Exception as e:
                                 print(f"Match Error: {e}")

                        else:
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "A+", "callback_data": "req_blood_A+"}, {"text": "A-", "callback_data": "req_blood_A-"}],
                                    [{"text": "B+", "callback_data": "req_blood_B+"}, {"text": "B-", "callback_data": "req_blood_B-"}],
                                    [{"text": "O+", "callback_data": "req_blood_O+"}, {"text": "O-", "callback_data": "req_blood_O-"}],
                                    [{"text": "AB+", "callback_data": "req_blood_AB+"}, {"text": "AB-", "callback_data": "req_blood_AB-"}]
                                ]
                            }
                            send_telegram_message(chat_id, "Please select a blood group to request:", reply_markup=keyboard)

    if "channel_post" in data:
        print(f"DEBUG: Received channel_post: {data['channel_post']}")
        msg = data["channel_post"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        
        # Only process if meaningful text
        if text and len(text) > 5 and not text.startswith("/"):
             print(f"DEBUG: Parsing text: {text}")
             parsed = parse_request_with_ai(text)
             print(f"DEBUG: Parsed result: {parsed}")
             
             if parsed and parsed.get("blood_type"):
                 # Create Request (Requester = Channel itself)
                 # Ensure Channel is in 'users' table? Or just allow requests from IDs not in users?
                 # Foreign key constraint might exist. Let's risk it or insert channel as user first.
                 
                 # Optimization: Allow unknown requester for channel posts OR auto-register channel
                 # Attempting to lazy-register channel if strict FK exists
                 try:
                     # Use unique pseudo-phone for channel
                     pseudo_phone = f"channel_{chat_id}" 
                     print(f"DEBUG: Registering Channel {chat_id} with phone {pseudo_phone}")
                     
                     user_data = {
                         "telegram_id": chat_id,
                         "full_name": msg["chat"].get("title", "Channel Admin"),
                         "phone_number": pseudo_phone,
                         "status": "active", # Ensure active
                         "role": "admin"
                     }
                     # Upsert to handle existing or new
                     supabase.table("users").upsert(user_data).execute()
                     print("DEBUG: Channel Registration Successful")
                 except Exception as e:
                     print(f"DEBUG: Channel Registration FAILED: {e}")
                     # If registration failed and user doesn't exist, Next step will fail.
                     # But maybe it failed because it exists? Upsert shouldn't fail on existence.
                     # If it failed on something else, we should probably return.
                     # allow to proceed just in case valid error (like 'already exists' but upsert handles that?)

                 
                 # Create Request
                 req_data = {
                      "requester_id": chat_id,
                      "blood_type": parsed['blood_type'],
                      "location": parsed.get('location', 'Unknown'),
                      "urgency": parsed.get('urgency', 'Normal'),
                      "is_active": True
                 }
                 res = supabase.table("requests").insert(req_data).execute()
                 req_id = res.data[0]['id']
                 
                 # Post Formatted Message
                 from .utils import format_blood_request_message
                 msg_text = format_blood_request_message(
                     parsed['blood_type'], 
                     parsed.get('location', 'Unknown'), 
                     parsed.get('urgency', 'Normal'), 
                     user_data['full_name'], 
                     user_data['phone_number']
                 )
                 keyboard = {
                      "inline_keyboard": [[
                          {"text": "🙋♂️ I Can Help", "callback_data": f"help_{req_id}"}
                      ]]
                 }
                 sent = send_telegram_message(chat_id, msg_text, reply_markup=keyboard)
                 
                 if sent and sent.get("ok"):
                     msg_id = sent["result"]["message_id"]
                     supabase.table("requests").update({"telegram_message_id": msg_id}).eq("id", req_id).execute()

        return


@app.post("/api/update_last_donation")
async def update_last_donation(request: Request, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    try:
        data = await request.json()
        user_id = data.get("user_id")
        date_str = data.get("date")

        if not user_id or not date_str:
             return {"status": "error", "message": "Missing user_id or date"}

        # Update the user record
        res = supabase.table("villingili_users").update({"last_donation_date": date_str}).eq("telegram_id", user_id).execute()
        
        return {"status": "ok", "message": "Donation date updated"}
    except Exception as e:
        print(f"Update Donation Error: {e}")
        return {"status": "error", "message": str(e)}


# @app.post("/api/update_user")
# async def update_user(request: Request):
#    return {"status": "error", "message": "Deprecated. Use Pydantic endpoint."}


@app.post("/api/broadcast")
async def broadcast_message(request: Request, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    try:
        data = await request.json()
        message = data.get("message")
        
        if not message:
            return {"status": "error", "message": "Message content is required"}
            
        # Get all users with a telegram_id
        # In production, you might want to batch this or use a queue
        users_res = supabase.table("villingili_users").select("telegram_id").execute()
        users = users_res.data
        
        count = 0
        failed = 0
        
        for user in users:
            tid = user.get("telegram_id")
            if tid:
                try:
                    send_telegram_message(tid, message)
                    count += 1
                except Exception as e:
                    print(f"Failed to send to {tid}: {e}")
                    failed += 1
                    
        return {"status": "ok", "sent_count": count, "failed_count": failed}

    except Exception as e:
        print(f"Broadcast Error: {e}")
        return {"status": "error", "message": str(e)}


# @app.get("/api/get_admins")
# def get_admins():
#    pass

# @app.post("/api/create_admin")
# async def create_admin(request: Request):
#    pass

# @app.post("/api/update_password")
# async def update_password(request: Request):
#    pass

@app.post("/api/delete_admin")
async def delete_admin(request: Request, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")
        username = data.get("username")
        
        # Delete from admin_users
        query = supabase.table("villingili_admin_users").delete()
        if telegram_id:
             query = query.eq("telegram_id", telegram_id)
        elif username:
             query = query.eq("username", username)
        else:
             return {"status": "error", "detail": "Missing telegram_id or username"}
             
        res = query.execute()
        return {"status": "ok"}
    except Exception as e:
        print(f"Delete Admin Error: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/api/create_user")
async def create_user(request: Request, current_user: str = Depends(get_current_admin)):
    supabase = get_supabase_client()
    try:
        data = await request.json()
        
        # Check Duplicate Phone
        if data.get("phone_number"):
            existing = supabase.table("villingili_users").select("telegram_id").eq("phone_number", data["phone_number"]).execute()
            if existing.data:
                return {"status": "error", "detail": f"User with phone {data['phone_number']} already exists!"}
        
        # Validation
        if not data.get("phone_number") or not data.get("full_name"):
             return {"status": "error", "detail": "Name and Phone are required."}

        # Generate Fake ID (negative timestamp) if not provided
        import time
        fake_id = int(time.time() * -1) 
        
        final_tg_id = data.get("telegram_id")
        if not final_tg_id:
             final_tg_id = fake_id
        else:
             try:
                 final_tg_id = int(final_tg_id)
             except:
                 return {"status": "error", "detail": "Telegram ID must be a number."}

        # Prepare Data
        user_data = {
            "telegram_id": final_tg_id,
            "full_name": data["full_name"],
            "phone_number": data["phone_number"],
            "blood_type": data.get("blood_type"),
            "sex": data.get("sex"),
            "address": data.get("address"),
            "id_card_number": data.get("id_card_number"),
            "role": data.get("role", "user"),
            "status": "active"
        }
        
        # Execute Supabase Insert
        res = supabase.table("villingili_users").insert(user_data).execute()
        
        return {"status": "ok", "id": fake_id}
             
    except Exception as e:
        print(f"Create User Error: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/api/settings")
async def get_settings(current_user: str = Depends(get_current_admin)):
    return {
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHANNEL_ID": os.environ.get("TELEGRAM_CHANNEL_ID"),
        "ADMIN_GROUP_ID": os.environ.get("TELEGRAM_ADMIN_GROUP_ID"),
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        # Mask Key for security
        "SUPABASE_KEY": "HIDDEN", 
    }

@app.post("/api/settings")
async def update_settings(request: Request, current_user: str = Depends(get_current_admin)):
    try:
        data = await request.json()
        # Updates .env file crudely
        env_path = os.path.join(os.getcwd(), ".env")
        
        # Read existing
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        
        updates = {
            "TELEGRAM_BOT_TOKEN": data.get("TELEGRAM_BOT_TOKEN"),
            "TELEGRAM_CHANNEL_ID": data.get("TELEGRAM_CHANNEL_ID"),
            "TELEGRAM_ADMIN_GROUP_ID": data.get("ADMIN_GROUP_ID"), # Map Frontend name to Env name
            "SUPABASE_URL": data.get("SUPABASE_URL"),
            "SUPABASE_SERVICE_ROLE_KEY": data.get("SUPABASE_KEY") # Settings calls it KEY but likely means Service Role if Admin
        }
        
        # We need to actully update lines or append
        # This is a bit complex to do reliably in 10 lines, but basic approach:
        new_lines = []
        keys_handled = set()
        for line in lines:
            key = line.split("=")[0].strip()
            if key in updates and updates[key]:
                new_lines.append(f"{key}={updates[key]}\n")
                keys_handled.add(key)
            else:
                new_lines.append(line)
        
        for k, v in updates.items():
            if k not in keys_handled and v:
                new_lines.append(f"{k}={v}\n")
        
        with open(env_path, "w") as f:
            f.writelines(new_lines)
            
        # Also update memory
        for k, v in updates.items():
            if v: os.environ[k] = v
            
        return {"status": "ok", "message": "Settings Updated (Restart might be needed)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    # print(f"Update: {data}")
    await process_update(data)
    return {"status": "ok"}


# Serve Index for Root and SPA Catch-All
@app.get("/favicon.png")
async def favicon():
    file_path = os.path.join(dist_dir, "favicon.png")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "Favicon not found"}, status_code=404)

@app.get("/")
@app.get("/{rest_of_path:path}")
async def serve_spa(rest_of_path: str = ""):
    if rest_of_path.startswith("api/"):
        return JSONResponse({"error": "API route not found"}, status_code=404)

    # Search locations for index.html
    # 1. Check if it's a static file in dist_dir (e.g. favicon.png)
    file_path = os.path.join(dist_dir, rest_of_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    # 2. Search locations for index.html (SPA Fallback)
    possible_paths = [
        os.path.join(dist_dir, "index.html"),
        os.path.join(base_dir, "frontend", "dist", "index.html"),
        os.path.join(base_dir, "..", "frontend", "dist", "index.html"),
        os.path.join(os.getcwd(), "frontend", "dist", "index.html"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path)

    # Debug info if not found
    cwd = os.getcwd()
    try:
        dist_contents = os.listdir(dist_dir) if os.path.exists(dist_dir) else "OPEN_FAIL"
    except:
        dist_contents = "ERR"
        
    return JSONResponse({
        "error": "Frontend Not Found", 
        "searched_paths": possible_paths,
        "cwd": cwd,
        "dist_dir_exists": os.path.exists(dist_dir),
        "dist_contents": dist_contents
    }, status_code=404)
