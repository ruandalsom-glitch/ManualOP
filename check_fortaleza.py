import os
import json
import urllib.request
import urllib.parse

SUPABASE_URL = 'https://tgqjyyidogqxioqovhav.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRncWp5eWlkb2dxeGlvcW92aGF2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3Nzg4NjQsImV4cCI6MjA5NTM1NDg2NH0.Hprv50c9SB4aZXiQkWm49nutkN-Gde1Ve0OJR7mwTuk'

from datetime import datetime, timezone, timedelta
fuso_br = timezone(timedelta(hours=-3))
now_br = datetime.now(fuso_br)
data_alvo = now_br.strftime("%Y-%m-%d")

url = f"{SUPABASE_URL}/rest/v1/frota_escalas?select=*&data=eq.{data_alvo}&limit=500"
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        
        fortaleza = [d for d in data if d.get("praca") == "FORTALEZA"]
        print(f"Total Fortaleza entries today: {len(fortaleza)}")
        for d in fortaleza[-30:]:
            print(f"Coleta: {d.get('horario_coleta')} | Subpraca: {d.get('subpraca')} | Turno: {d.get('turno')} | Modal: {d.get('modal')} | L/S: {d.get('logados')}/{d.get('slots')}")
except Exception as e:
    import traceback
    traceback.print_exc()
