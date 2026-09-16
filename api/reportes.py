import os
import sys
import json
from http.server import BaseHTTPRequestHandler

# Tenta importar sincronização com o Supabase
try:
    from api.sync_reportes_supabase import sincronizar_jira_com_supabase
except ImportError:
    try:
        from sync_reportes_supabase import sincronizar_jira_com_supabase
    except ImportError:
        sincronizar_jira_com_supabase = None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        msg = "Sincronizacao de reportes executada."
        if sincronizar_jira_com_supabase:
            try:
                sincronizar_jira_com_supabase()
                msg = "Sincronizacao de reportes realizada com sucesso."
            except Exception as e:
                msg = f"Sincronizacao parcial: {str(e)}"
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        res = {"status": "ok", "message": msg}
        self.wfile.write(json.dumps(res).encode('utf-8'))
        return

    def do_POST(self):
        self.do_GET()
