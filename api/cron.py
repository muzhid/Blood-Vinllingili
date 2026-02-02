from fastapi import FastAPI
from .utils import get_supabase_client, send_telegram_message
import os

app = FastAPI()

# Note: This file needs to be imported by index.py or routed correctly.
# In Vercel, we can point the cron path to this file or add a route in index.py
# Let's add it to index.py instead to keep it simple with the single entry point.
