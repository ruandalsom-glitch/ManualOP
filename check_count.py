import urllib.request
import json
from datetime import datetime, timezone, timedelta

SUPABASE_URL = 'https://wpuyanodymsjzsqzbmfy.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwdXlhbm9keW1zanpzcXpibWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1NTA1NzQsImV4cCI6MjEwMjEyNjU3NH0.iKaC2aOd6lKhxMPyRXWQ02Eu6Eesdc_rYckYr_fp02o'

fuso_br = timezone(timedelta(hours=-3))
ontem = (datetime.now(fuso_br) - timedelta(days=1)).strftime("%Y-%m-%d")

url_count = f"{SUPABASE_URL}/rest/v1/frota_metricas?select=id&horario=like.{ontem}%"
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=exact"}

try:
    req = urllib.request.Request(url_count, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content_range = resp.getheader('content-range')
        print(f"Total entries yesterday ({ontem}): {content_range}")
except Exception as e:
    print(f"Erro: {e}")
