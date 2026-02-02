import requests

try:
    print("Testing API Connection at http://localhost:8000/api/users ...")
    res = requests.get("http://localhost:8000/api/users")
    print(f"Status Code: {res.status_code}")
    print(f"Content Start: {res.text[:200]}")
except Exception as e:
    print(f"API Connection Failed: {e}")
