import json
import urllib.request
import urllib.parse

SUPABASE_URL = 'https://wpuyanodymsjzsqzbmfy.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwdXlhbm9keW1zanpzcXpibWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1NTA1NzQsImV4cCI6MjEwMjEyNjU3NH0.iKaC2aOd6lKhxMPyRXWQ02Eu6Eesdc_rYckYr_fp02o'

url = f"{SUPABASE_URL}/rest/v1/frota_escalas?select=*&data=eq.2026-07-08&limit=1"
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        print("Success! Got 1 record.")
except Exception as e:
    print(f"Error limit=1: {e}")

url = f"{SUPABASE_URL}/rest/v1/frota_escalas?select=*&data=eq.2026-07-08"
headers['Range'] = "0-999"

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Success! Range 0-999 got {len(data)} records.")
except Exception as e:
    print(f"Error Range 0-999: {e}")

headers['Range'] = "3000-3999"
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Success! Range 3000-3999 got {len(data)} records.")
except Exception as e:
    print(f"Error Range 3000-3999: {e}")
