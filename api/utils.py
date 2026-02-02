import os
import json
from supabase import create_client, Client
from openai import OpenAI

from .local_db import LocalDB

def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Use real Supabase if configured and NOT pointing to localhost (unless intended)
    # Simple check: if we have keys and it's not the default placeholder
    if url and key and "localhost:8000" not in url:
        try:
            return create_client(url, key)
        except Exception as e:
            print(f"Supabase Connection Failed: {e}, falling back to LocalDB")
            
    return LocalDB()

def parse_request_with_ai(text: str):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OpenAI API key missing.")
        return None
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are an expert entity extractor for a Maldivian blood donation system.
    Extract the following fields from the user input:
    - blood_type: (e.g., A+, B-, O+, AB+) - Normalize to standard format.
    - location: (e.g., IGMH, ADK, Siwad Hospital) - If missing, try to infer from context or leave null.
    - urgency: 'High' or 'Normal'. defaults to 'Normal' if not specified or implied.
    
    Input may be in English or Dhivehi (Latin).
    Return ONLY a JSON object: {"blood_type": "...", "location": "...", "urgency": "..."}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error parsing with AI: {e}")
        return None

def send_telegram_message(chat_id: int, text: str, reply_markup=None):
    # This function will rely on the bot token in env
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    # Mock Mode Check
    if os.environ.get("MOCK_TELEGRAM") == "true" or not token:
        msg_log = f"\n[BOT REPLIED] Chat: {chat_id}\nMessage: {text}\nKB: {reply_markup}\n{'-'*30}\n"
        print(msg_log, flush=True)
        # Also write to a file for easier reading
        with open("bot_replies.log", "a", encoding="utf-8") as f:
            f.write(msg_log)
        return {"ok": True}

    if not token:
        print("Warning: Telegram Bot Token missing.")
        return None
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return None

def edit_telegram_message(chat_id: int, message_id: int, text: str, reply_markup=None):
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
        
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error editing Telegram message: {e}")
        return None

def answer_callback_query(callback_query_id: str, text: str = None, show_alert: bool = False, url: str = None):
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
        
    url_api = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    if url:
        payload["url"] = url
        
    try:
        requests.post(url_api, json=payload)
    except Exception as e:
        print(f"Error answering callback: {e}")


def check_and_prompt_missing_info(user_id: int, user_data: dict):
    # 1. Blood Type
    if not user_data.get("blood_type"):
        keyboard = {
            "inline_keyboard": [
                [{"text": "A+", "callback_data": "set_blood_A+"}, {"text": "A-", "callback_data": "set_blood_A-"}],
                [{"text": "B+", "callback_data": "set_blood_B+"}, {"text": "B-", "callback_data": "set_blood_B-"}],
                [{"text": "O+", "callback_data": "set_blood_O+"}, {"text": "O-", "callback_data": "set_blood_O-"}],
                [{"text": "AB+", "callback_data": "set_blood_AB+"}, {"text": "AB-", "callback_data": "set_blood_AB-"}]
            ]
        }
        send_telegram_message(user_id, "🩸 Please select your **Blood Type**:", reply_markup=keyboard)
        return

    # 2. Sex
    if not user_data.get("sex"):
        keyboard = {
            "inline_keyboard": [
                [{"text": "Male", "callback_data": "set_sex_Male"}, {"text": "Female", "callback_data": "set_sex_Female"}]
            ]
        }
        send_telegram_message(user_id, "⚧ Please select your **Sex**:", reply_markup=keyboard)
        return

    # 3. ID Card Number
    if not user_data.get("id_card_number"):
        force_reply = {"force_reply": True, "input_field_placeholder": "A123456"}
        send_telegram_message(user_id, "🆔 Please reply with your **ID Card Number**:", reply_markup=force_reply)
        return

    # 4. Address/Island
    if not user_data.get("address"):
        force_reply = {"force_reply": True, "input_field_placeholder": "e.g. Male', Addu..."}
        send_telegram_message(user_id, "🏠 Please enter your **Address**:", reply_markup=force_reply)
        return

    # All good
    msg_text = (
        f"✅ <b>Profile Complete!</b>\n\n"
        f"👤 <b>Name:</b> {user_data.get('full_name')}\n"
        f"🩸 <b>Blood:</b> {user_data.get('blood_type')}\n"
        f"⚧ <b>Sex:</b> {user_data.get('sex')}\n"
        f"🆔 <b>ID:</b> {user_data.get('id_card_number')}\n"
        f"🏠 <b>Loc:</b> {user_data.get('address')}"
    )
    keyboard = {
        "keyboard": [[{"text": "👋 Welcome Back!"}]],
        "resize_keyboard": True
    }
    send_telegram_message(user_id, msg_text, reply_markup=keyboard)

def analyze_id_card_with_ai(image_url: str):
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    prompt = """
    Analyze this image. Is it a Maldives National Identity Card?
    If NO, return {"is_valid": false}.
    If YES, extract:
    - full_name (English Name)
    - id_card_number (e.g., A123456)
    - sex (M or F)
    - address (English Address part only, typically at bottom left)
    
    Return JSON: {"is_valid": true, "full_name": "...", "id_card_number": "...", "sex": "...", "address": "..."}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ],
                }
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Vision Error: {e}")
        return None

def format_blood_request_message(blood_type, location, urgency, req_name, req_phone):
    lines = [f"🚨 <b>BLOOD REQUEST</b>", f"Type: {blood_type}"]
    
    # Hide location if default or unknown
    if location and location not in ["Not Specified", "Unknown", "None"]:
        lines.append(f"Location: {location}")
        
    # Hide urgency if not High/Critical
    if urgency and urgency in ["High", "Critical", "Urgent"]:
        lines.append(f"Urgency: {urgency}")
        
    lines.append(f"Requester: {req_name} - {req_phone}")
    
    return "\n".join(lines)
