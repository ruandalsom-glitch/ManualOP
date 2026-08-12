import os
import requests
from datetime import datetime

SUPABASE_URL = "https://wpuyanodymsjzsqzbmfy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwdXlhbm9keW1zanpzcXpibWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1NTA1NzQsImV4cCI6MjEwMjEyNjU3NH0.iKaC2aOd6lKhxMPyRXWQ02Eu6Eesdc_rYckYr_fp02o"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

url = f"{SUPABASE_URL}/rest/v1/frota_pedidos_heatmap?select=origin_lat,origin_lng,created_at"

response = requests.get(url, headers=headers)
print("Status Code:", response.status_code)
data = response.json()
print("Number of records matched:", len(data))
if len(data) > 0:
    print("First record:", data[0])
