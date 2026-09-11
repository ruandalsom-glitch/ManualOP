import os
import sys
import json
import re
import datetime
import pickle
import gspread
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# CONFIGURAÇÕES
# ============================================================
PLANILHA_URL     = "https://docs.google.com/spreadsheets/d/1ChubWCQ7pjbbgis2TAda_oSxXzor1fhgDarcX4Yu-bE/edit"
ABA_NOME         = "ReportesColaboradores"
CREDENCIAIS_JSON = "C:/escalas/client_secret_246955343617-2b2lc3lvasat9aa8lbb7up36k6n2ed8a.apps.googleusercontent.com.json"
TOKEN_PATH       = "C:/escalas/token_escalas.pkl"
SCOPES           = ["https://www.googleapis.com/auth/spreadsheets"]

BASE_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DATA_PATH   = os.path.join(BASE_DIR, "jira_reports_data.json")

COLUNAS = [
    "Data", "Categoria", "descricao", "ticket", "Plataforma", "SLA", "Prazo", "Status", "Dados", "Atendente", "Obs"
]

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
    """Converte strings de datas extraídas do Jira (ex: '09/set/26 18:03', '29/8/2026', '2026-08-29') para datetime"""
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    # Formato DD/mmm/YY HH:MM (ex: 09/set/26 18:03 ou 29/ago/2026 12:47)
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

    # Formato DD/MM/YYYY ou DD/MM/YY (ex: 14/08/2026 17:34)
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
    """Calcula se o chamado está finalizado, no prazo ou em atraso (com número de dias)"""
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
        atraso = dias_decorridos - sla_val
        return f"Em atraso ({dias_decorridos} dias)"
    else:
        return "No prazo"

def conectar_sheets():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENCIAIS_JSON, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    client = gspread.authorize(creds)
    planilha = client.open_by_url(PLANILHA_URL)

    try:
        aba = planilha.worksheet(ABA_NOME)
    except Exception:
        print(f"Aba '{ABA_NOME}' não encontrada. Criando nova aba...")
        aba = planilha.add_worksheet(title=ABA_NOME, rows="500", cols="15")
        aba.append_row(COLUNAS)
        aba.format("A1:K1", {
            "backgroundColor": {"red": 0.172, "green": 0.403, "blue": 0.917}, # Azul #2C67EA
            "horizontalAlignment": "CENTER",
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1, "green": 1, "blue": 1}
            }
        })

    return aba

def sincronizar_jira_com_sheets():
    print("=" * 60)
    print("📊 Sincronizando Chamados do Jira com a planilha ReportesColaboradores...")
    print("=" * 60)

    if not os.path.exists(JSON_DATA_PATH):
        print(f"❌ Arquivo {JSON_DATA_PATH} não encontrado.")
        return

    with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
        jira_data = json.load(f)

    print(f"Carregados {len(jira_data)} chamados do arquivo JSON.")

    aba = conectar_sheets()
    todas_linhas = aba.get_all_values()

    # Se a tabela estiver vazia ou sem cabeçalho, insere o cabeçalho
    if not todas_linhas:
        aba.append_row(COLUNAS)
        todas_linhas = [COLUNAS]

    # Indexar linhas existentes pelo código do ticket (Coluna D -> index 3)
    ticket_row_map = {}
    for idx, row in enumerate(todas_linhas):
        if idx == 0:
            continue
        ticket_key = row[3].strip() if len(row) > 3 else ""
        if ticket_key:
            ticket_row_map[ticket_key] = idx + 1 # 1-based index no Sheets

    novas_linhas = []
    atualizacoes = []

    for item in jira_data:
        ticket = item.get("issue_key", "").strip()
        if not ticket:
            continue

        categoria = item.get("type", "Geral")
        descricao = item.get("summary", "")
        status = item.get("status", "Aberto")
        atendente = item.get("reporter", "Não Identificado")
        data_reporte = item.get("created_date", "") or item.get("response_date", "") or datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Resposta / Atividade como Dados
        dados_resp = ""
        if item.get("response_text"):
            dados_resp = f"{item.get('response_author', 'Atendente')}: {item.get('response_text')}"

        plataforma = "EntreGô / Jira"
        sla = "2 dias"
        prazo = calcular_prazo(data_reporte, status, sla_dias=2)
        obs = ""

        linha_desejada = [
            data_reporte,  # Coluna A: Data
            categoria,     # Coluna B: Categoria
            descricao,     # Coluna C: descricao
            ticket,        # Coluna D: ticket
            plataforma,    # Coluna E: Plataforma
            sla,           # Coluna F: SLA
            prazo,         # Coluna G: Prazo (ex: Em atraso (3 dias), Finalizado, No prazo)
            status,        # Coluna H: Status
            dados_resp,    # Coluna I: Dados
            atendente,     # Coluna J: Atendente (Nome do Colaborador)
            obs            # Coluna K: Obs
        ]

        if ticket in ticket_row_map:
            row_idx = ticket_row_map[ticket]
            # Atualiza apenas os campos dinâmicos preservando SLA / Obs se editados
            row_existente = todas_linhas[row_idx - 1]
            plataforma_exist = row_existente[4] if len(row_existente) > 4 and row_existente[4] else plataforma
            sla_exist = row_existente[5] if len(row_existente) > 5 and row_existente[5] else sla
            obs_exist = row_existente[10] if len(row_existente) > 10 else obs

            prazo_calc = calcular_prazo(data_reporte, status, sla_exist)

            linha_atualizada = [
                data_reporte, categoria, descricao, ticket,
                plataforma_exist, sla_exist, prazo_calc, status,
                dados_resp, atendente, obs_exist
            ]

            atualizacoes.append({
                "range": f"A{row_idx}:K{row_idx}",
                "values": [linha_atualizada]
            })
        else:
            novas_linhas.append(linha_desejada)

    # Executa atualizações em batch para evitar rate limit
    if atualizacoes:
        print(f"🔄 Atualizando {len(atualizacoes)} linhas existentes no Google Sheets...")
        aba.batch_update(atualizacoes)

    if novas_linhas:
        print(f"➕ Inserindo {len(novas_linhas)} novos chamados no Google Sheets...")
        aba.append_rows(novas_linhas)

    print("✅ Sincronização com o Google Sheets finalizada com sucesso!")

if __name__ == "__main__":
    sincronizar_jira_com_sheets()
