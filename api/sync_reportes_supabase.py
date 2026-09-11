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
    print("⚡ Sincronizando Webscraping do Jira com a tabela 'reportes_colaboradores' no Supabase...")
    print("=" * 60)

    if not os.path.exists(JSON_DATA_PATH):
        print(f"❌ Arquivo {JSON_DATA_PATH} não encontrado.")
        return

    with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
        jira_data = json.load(f)

    print(f"Carregados {len(jira_data)} chamados do Jira.")

    payload = []
    for item in jira_data:
        ticket = item.get("issue_key", "").strip()
        if not ticket:
            continue

        categoria = item.get("type", "Geral")
        descricao = item.get("summary", "")
        status = item.get("status", "Aberto")
        atendente = item.get("reporter", "Não Identificado")
        data_reporte = item.get("created_date", "") or item.get("response_date", "") or datetime.datetime.now().strftime("%d/%m/%Y")
        
        dados_resp = ""
        if item.get("response_text"):
            dados_resp = f"{item.get('response_author', 'Atendente')}: {item.get('response_text')}"

        plataforma = "EntreGô / Jira"
        sla = "2 dias"
        prazo = calcular_prazo(data_reporte, status, sla_dias=2)

        payload.append({
            "data": data_reporte,
            "categoria": categoria,
            "descricao": descricao,
            "ticket": ticket,
            "plataforma": plataforma,
            "sla": sla,
            "prazo": prazo,
            "status": status,
            "dados": dados_resp,
            "atendente": atendente,
            "obs": ""
        })

    if not payload:
        print("Nenhum chamado válido para enviar.")
        return

    # Fazer Upsert no Supabase via REST API (on_conflict=ticket, resolution=merge-duplicates)
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/reportes_colaboradores?on_conflict=ticket"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    # Enviar em lotes de 100
    lote_size = 100
    for i in range(0, len(payload), lote_size):
        lote = payload[i:i+lote_size]
        body_bytes = json.dumps(lote, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                print(f"  [Lote {i//lote_size + 1}] {len(lote)} registros salvos/atualizados no Supabase (Status: {resp.status})")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            print(f"❌ Erro HTTP ao enviar para o Supabase ({e.code}): {err_body}")
        except Exception as e:
            print(f"❌ Erro ao conectar com o Supabase: {e}")

    print("✅ Sincronização direta Jira -> Supabase finalizada com sucesso!")

if __name__ == "__main__":
    sincronizar_jira_com_supabase()
