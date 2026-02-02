from api.utils import get_supabase_client
import sys

def reset_db():
    print("⚠️  WARNING: This will DELETE ALL DATA from 'users' and 'requests' tables.")
    confirm = input("Type 'yes' to continue: ")
    if confirm != 'yes':
        print("Aborted.")
        return

    supabase = get_supabase_client()
    
    # Supabase Delete All requires a filter that matches all.
    # We'll use neq '0' for IDs (assuming UUID or int, usually works if type matches roughly or just arbitrary non-match)
    
    print("Deleting Requests...")
    try:
        # Assuming ID is int8 or UUID. neq 0 usually works for "all" if there is no ID 0.
        supabase.table("requests").delete().neq("id", 0).execute()
    except Exception as e:
        print(f"Error filtering requests (trying alternative): {e}")
        # If requests uses UUID id
        supabase.table("requests").delete().neq("location", "impossible_value_xyz").execute()

    print("Deleting Users...")
    try:
        supabase.table("users").delete().neq("telegram_id", 0).execute()
    except Exception as e:
        print(f"Error filtering users: {e}")

    print("✅ Database Reset Complete.")

if __name__ == "__main__":
    reset_db()
