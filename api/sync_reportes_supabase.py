import os
import sys
import json
import urllib.request
import urllib.parse
import re
import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# CONFIGURAÇÕES SUPABASE
# ============================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wpuyanodymsjzsqzbmfy.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwdXlhbm9keW1zanpzcXpibWZ5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjU1MDU3NCwiZXhwIjoyMTAyMTI2NTc0fQ.tMWHNa44-IkcQK63S2aRDHZbxMP-8nlZ9SP2LY97BLo")

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DATA_PATH = os.path.join(BASE_DIR, "jira_reports_data.json")

MESES_MAP = {
    'jan': 1, 'janeiro': 1,
    'fev': 2, 'fevereiro': 2,
    'mar': 3, 'março': 3, 'marco': 3,
    'abr': 4, 'abril': 4,
    'mai': 5, 'maio': 5,
    'jun': 6, 'junho': 6,
    'jul': 7, 'julho': 7,
    'ago': 8, 'agosto': 8,
    'set': 9, 'setembro': 9,
    'out': 10, 'outubro': 10,
    'nov': 11, 'novembro': 11,
    'dez': 12, 'dezembro': 12
}

def parse_date_to_datetime(date_str):
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    m1 = re.search(r'(\d{1,2})/([a-zA-ZçÇ]+)/(\d{2,4})(?:\s+(\d{1,2}):(\d{2}))?', date_str)
    if m1:
        dia = int(m1.group(1))
        mes_name = m1.group(2).lower()
        ano = int(m1.group(3))
        if ano < 100: ano += 2000
        mes = MESES_MAP.get(mes_name, 1)
        hora = int(m1.group(4)) if m1.group(4) else 0
        minuto = int(m1.group(5)) if m1.group(5) else 0
        try:
            return datetime.datetime(ano, mes, dia, hora, minuto)
        except Exception:
            pass

    m2 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})(?:\s+(\d{1,2}):(\d{2}))?', date_str)
    if m2:
        dia = int(m2.group(1))
        mes = int(m2.group(2))
        ano = int(m2.group(3))
        if ano < 100: ano += 2000
        hora = int(m2.group(4)) if m2.group(4) else 0
        minuto = int(m2.group(5)) if m2.group(5) else 0
        try:
            return datetime.datetime(ano, mes, dia, hora, minuto)
        except Exception:
            pass

    return None

def calcular_prazo(created_date_str, status_str, sla_dias=2):
    st = (status_str or '').lower().strip()
    
    if any(k in st for k in ['conclu', 'resolv', 'fechad', 'cancelad', 'finaliz']):
        return "Finalizado"

    dt_criacao = parse_date_to_datetime(created_date_str)
    if not dt_criacao:
        return "Em andamento"

    hoje = datetime.datetime.now()
    dias_decorridos = (hoje.date() - dt_criacao.date()).days

    try:
        sla_val = int(str(sla_dias).replace('dias', '').replace('d', '').strip())
    except Exception:
        sla_val = 2

    if dias_decorridos > sla_val:
        return f"Em atraso ({dias_decorridos} dias)"
    else:
        return "No prazo"

def sincronizar_jira_com_supabase():
    print("=" * 60)
    print("⚡ Sincronizando Webscraping do Jira e Google Sheets com a tabela 'reportes_colaboradores' no Supabase...")
    print("=" * 60)

    # 1. Tenta carregar dados do Google Sheets primeiro (que possui Setor, Solicitante e Obs)
    sheets_data_map = {}
    try:
        import gspread
        import pickle
        PLANILHA_URL = "https://docs.google.com/spreadsheets/d/1ChubWCQ7pjbbgis2TAda_oSxXzor1fhgDarcX4Yu-bE/edit"
        ABA_NOME     = "ReportesColaboradores"
        TOKEN_PATH   = "C:/escalas/token_escalas.pkl"

        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)
            client = gspread.authorize(creds)
            planilha = client.open_by_url(PLANILHA_URL)
            aba = planilha.worksheet(ABA_NOME)
            rows = aba.get_all_values()
            if rows and len(rows) > 1:
                for r in rows[1:]:
                    t_key = r[3].strip() if len(r) > 3 else ""
                    if t_key:
                        sheets_data_map[t_key] = {
                            "data": r[0] if len(r) > 0 else "",
                            "categoria": r[1] if len(r) > 1 else "",
                            "descricao": r[2] if len(r) > 2 else "",
                            "plataforma": r[4] if len(r) > 4 else "",
                            "sla": r[5] if len(r) > 5 else "",
                            "prazo": r[6] if len(r) > 6 else "",
                            "status": r[7] if len(r) > 7 else "",
                            "setor": r[8] if len(r) > 8 and r[8].strip() else "Geral",
                            "dados": r[9] if len(r) > 9 else "",
                            "atendente": r[10] if len(r) > 10 else "",
                            "obs": r[11] if len(r) > 11 else ""
                        }
                print(f"Loaded {len(sheets_data_map)} rows from Google Sheets ReportesColaboradores.")
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível ler diretamente do Google Sheets: {e}")

    # 2. Carrega chamados do Jira (json)
    jira_data = []
    if os.path.exists(JSON_DATA_PATH):
        with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
            jira_data = json.load(f)
        print(f"Carregados {len(jira_data)} chamados do arquivo JSON Jira.")

    # 3. Busca registros existentes no Supabase para mapear ticket -> id
    url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reportes_colaboradores?select=id,ticket,setor,atendente,data"
    req_get = urllib.request.Request(url_get, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    
    existentes_map = {}
    try:
        with urllib.request.urlopen(req_get) as resp:
            raw_res = json.loads(resp.read().decode('utf-8'))
            for r in raw_res:
                t = (r.get("ticket") or "").strip()
                if t:
                    existentes_map[t] = r.get("id")
    except Exception as e:
        print(f"Erro ao buscar existentes no Supabase: {e}")

    # Processa Jira items ou Sheets items
    payload_existentes = []
    payload_novos = []
    processed_tickets = set()

    # Processa primeiro itens do Google Sheets (prioritário por conter setor/atendente)
    for ticket, s_item in sheets_data_map.items():
        processed_tickets.add(ticket)
        item = {
            "data": s_item["data"],
            "categoria": s_item["categoria"],
            "descricao": s_item["descricao"],
            "ticket": ticket,
            "plataforma": s_item["plataforma"],
            "sla": s_item["sla"],
            "prazo": s_item["prazo"],
            "status": s_item["status"],
            "setor": s_item["setor"],
            "dados": s_item["dados"],
            "atendente": s_item["atendente"],
            "obs": s_item["obs"]
        }
        if ticket in existentes_map:
            item["id"] = existentes_map[ticket]
            payload_existentes.append(item)
        else:
            payload_novos.append(item)

    # Adiciona itens do Jira que ainda não foram processados pelo Sheets
    for item_j in jira_data:
        ticket = item_j.get("issue_key", "").strip()
        if not ticket or ticket in processed_tickets:
            continue

        processed_tickets.add(ticket)
        categoria = item_j.get("type", "Geral")
        descricao = item_j.get("summary", "")
        status = item_j.get("status", "Aberto")
        data_reporte = item_j.get("created_date", "") or item_j.get("response_date", "") or datetime.datetime.now().strftime("%d/%m/%Y")
        
        dados_resp = ""
        raw_resp = item_j.get("response_text", "")
        if raw_resp and not raw_resp.lower().startswith("abrir ") and not raw_resp.lower().endswith(".jpg"):
            dados_resp = f"{item_j.get('response_author', 'Atendente Jira')}: {raw_resp}"

        plataforma = "EntreGô / Jira"
        sla = "2 dias"
        prazo = calcular_prazo(data_reporte, status, sla_dias=2)
        setor = item_j.get("setor", "Geral")

        item = {
            "data": data_reporte,
            "categoria": categoria,
            "descricao": descricao,
            "ticket": ticket,
            "plataforma": plataforma,
            "sla": sla,
            "prazo": prazo,
            "status": status,
            "setor": setor,
            "dados": dados_resp,
            "atendente": "",
            "obs": ""
        }
        if ticket in existentes_map:
            item["id"] = existentes_map[ticket]
            payload_existentes.append(item)
        else:
            payload_novos.append(item)

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    if payload_existentes:
        url_upsert = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reportes_colaboradores?on_conflict=id"
        body = json.dumps(payload_existentes, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url_upsert, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"  [Update Lote] {len(payload_existentes)} registros existentes sincronizados no Supabase.")
        except Exception as e:
            print(f"❌ Erro bulk update Supabase: {e}")

    if payload_novos:
        url_insert = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reportes_colaboradores"
        body = json.dumps(payload_novos, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url_insert, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"  [Inserção Lote] {len(payload_novos)} novos registros inseridos no Supabase.")
        except Exception as e:
            print(f"❌ Erro bulk insert Supabase: {e}")

    print("✅ Sincronização Jira/Sheets -> Supabase concluída com sucesso!")

if __name__ == "__main__":
    sincronizar_jira_com_supabase()
