import asyncio
from playwright.async_api import async_playwright
import sys
import os
import json
import datetime
import re

# Tenta importar sincronização com o Google Sheets
try:
    from api.sync_reportes_sheets import sincronizar_jira_com_sheets
except ImportError:
    try:
        from sync_reportes_sheets import sincronizar_jira_com_sheets
    except ImportError:
        sincronizar_jira_com_sheets = None

# Tenta importar sincronização com o Supabase
try:
    from api.sync_reportes_supabase import sincronizar_jira_com_supabase
except ImportError:
    try:
        from sync_reportes_supabase import sincronizar_jira_com_supabase
    except ImportError:
        sincronizar_jira_com_supabase = None

sys.stdout.reconfigure(encoding='utf-8')

JIRA_USER = "ruan.dalson@entregospsumarezinho.com.br"
JIRA_PASS = "Ruankz100%"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_OUTPUT_PATH = os.path.join(BASE_DIR, "jira_reports_data.json")

# Lista exata das 4 categorias permitidas
ALLOWED_TYPES = [
    "Contestação de Promoção",
    "Problemas Cadastrais",
    "Contestação de Garantido FE",
    "Dúvidas Gerais"
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

def parse_created_date(text):
    """Normaliza e formata datas de criação extraídas do Jira"""
    if not text:
        return ""

    m = re.search(r'criou essa solicitação em\s+(.+)$', text, re.IGNORECASE)
    val = m.group(1).strip() if m else text.strip()

    now = datetime.datetime.now()
    val_lower = val.lower()

    if "hoje" in val_lower:
        time_part = re.search(r'(\d{1,2}:\d{2})', val_lower)
        h, m = time_part.group(1).split(':') if time_part else (0, 0)
        dt = now.replace(hour=int(h), minute=int(m))
        return dt.strftime("%d/%m/%Y %H:%M")
    elif "ontem" in val_lower:
        time_part = re.search(r'(\d{1,2}:\d{2})', val_lower)
        h, m = time_part.group(1).split(':') if time_part else (0, 0)
        dt = (now - datetime.timedelta(days=1)).replace(hour=int(h), minute=int(m))
        return dt.strftime("%d/%m/%Y %H:%M")

    m1 = re.search(r'(\d{1,2})/([a-zA-ZçÇ]+)/(\d{2,4})(?:\s+(\d{1,2}:\d{2}))?', val)
    if m1:
        dia = int(m1.group(1))
        mes_str = m1.group(2).lower()
        ano = int(m1.group(3))
        if ano < 100: ano += 2000
        mes = MESES_MAP.get(mes_str, 1)
        time_str = m1.group(4) or "00:00"
        return f"{dia:02d}/{mes:02d}/{ano} {time_str}"

    m2 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})(?:\s+(\d{1,2}:\d{2}))?', val)
    if m2:
        dia = int(m2.group(1))
        mes = int(m2.group(2))
        ano = int(m2.group(3))
        if ano < 100: ano += 2000
        time_str = m2.group(4) or "00:00"
        return f"{dia:02d}/{mes:02d}/{ano} {time_str}"

    return val

def map_and_filter_type(type_raw, summary):
    """Mapeia e valida se o chamado pertence a uma das 4 categorias permitidas"""
    t = (type_raw or '').strip()
    s = (summary or '').strip().lower()
    t_lower = t.lower()

    if "contestação de promoção" in t_lower or "contestacao de promocao" in t_lower or "contestação de promoção" in s or "contestacao de promocao" in s:
        return "Contestação de Promoção"

    if "problemas cadastrais" in t_lower or "bug" in t_lower or "cadastral" in t_lower or "modal" in s or "erro" in s or "falha" in s or "bug" in s:
        return "Problemas Cadastrais"

    if "garantido" in t_lower or "garantido" in s:
        return "Contestação de Garantido FE"

    if "dúvidas gerais" in t_lower or "duvidas gerais" in t_lower or "dúvida" in s or "duvida" in s or "geral" in t_lower:
        return "Dúvidas Gerais"

    return None

async def fetch_issue_response(page, issue_key):
    """Navega até o detalhe do chamado e extrai data de criação, solicitante e última resposta/atividade humana"""
    url = f"https://ifood.atlassian.net/helpcenter/entrego/portal/4623/{issue_key}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(1800)

        content = await page.inner_text("body")
        lines = [l.strip() for l in content.split('\n') if l.strip()]

        response_author = ""
        response_date = ""
        response_text = ""
        created_date = ""
        reporter_found = ""

        for line in lines:
            if "criou essa solicitação em" in line:
                parts = line.split("criou essa solicitação em")
                reporter_found = parts[0].strip()
                created_date = parse_created_date(parts[1].strip())
                break
            elif "Solicitado em" in line:
                created_date = parse_created_date(line)
                break

        if "Atividade" in lines:
            idx = lines.index("Atividade")
            sub_lines = lines[idx + 1:]
            
            for i in range(len(sub_lines) - 2):
                author = sub_lines[i]
                date_str = sub_lines[i + 1]
                text_candidate = sub_lines[i + 2]

                if author != "Resposta automática" and "O status da sua" not in text_candidate and "Adicionar comentário" not in author:
                    if re.search(r'\d{2}/\w{3}/\d{2}', date_str) or "às" in date_str or ":" in date_str or "Ontem" in date_str or "Hoje" in date_str:
                        response_author = author
                        response_date = date_str
                        response_text = text_candidate
                        break

        return {
            "created_date": created_date,
            "reporter": reporter_found,
            "response_author": response_author,
            "response_date": response_date,
            "response_text": response_text
        }
    except Exception as e:
        return {"created_date": "", "reporter": "", "response_author": "", "response_date": "", "response_text": ""}

async def sync_jira_reports():
    print("=" * 60)
    print(f"🚀 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sincronizando Chamados Filtrados (Apenas 4 Categorias)...")
    print("=" * 60)

    extracted_reports = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("[1/4] Acessando portal de login SSO Atlassian...")
            login_url = "https://ifood.atlassian.net/helpcenter/entrego/user/login?destination=user%2Frequests"
            await page.goto(login_url)
            await page.wait_for_selector("#user-email", timeout=15000)

            print(f"[2/4] Autenticando conta: {JIRA_USER}...")
            await page.fill("#user-email", JIRA_USER)
            await page.click("button:has-text('Next'), button:has-text('Avançar')")
            await page.wait_for_timeout(2500)

            pass_btn = await page.query_selector("button:has-text('Continue with password'), button:has-text('Continuar com senha')")
            if pass_btn:
                await pass_btn.click()
                await page.wait_for_timeout(2500)

            pass_input = await page.query_selector("input[type='password'], #password")
            if pass_input:
                await pass_input.fill(JIRA_PASS)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(6000)

            print("[3/4] Acessando todos os chamados no Helpcenter EntreGô...")
            all_requests_url = "https://ifood.atlassian.net/helpcenter/entrego/user/requests?reporter=all&statuses=open,closed"
            await page.goto(all_requests_url)
            await page.wait_for_timeout(4000)

            print("   -> Executando rolagem dinâmica...")
            previous_count = 0
            max_scrolls = 35
            
            for scroll_idx in range(max_scrolls):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1200)

                current_rows = await page.query_selector_all("tbody tr")
                current_count = len(current_rows)

                if current_count == previous_count and current_count > 0:
                    break
                previous_count = current_count

            final_rows = await page.query_selector_all("tbody tr")
            print(f"\n[4/4] Filtrando e extraindo chamados pertencentes às 4 categorias solicitadas...")

            seen_keys = set()
            raw_issues = []

            for r in final_rows:
                text = await r.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]

                first_td = await r.query_selector("td:first-child")
                type_icon_alt = ""
                if first_td:
                    img = await first_td.query_selector("img")
                    if img:
                        type_icon_alt = await img.get_attribute("alt") or await img.get_attribute("title") or ""

                if len(lines) >= 3:
                    issue_key = ""
                    summary = ""
                    status = ""
                    reporter = ""

                    for idx, line in enumerate(lines):
                        if "SMENTGO-" in line:
                            issue_key = line
                            if idx + 1 < len(lines): summary = lines[idx + 1]
                            if idx + 2 < len(lines): status = lines[idx + 2]
                            if len(lines) > 3: reporter = lines[-1]
                            break

                    if issue_key and issue_key not in seen_keys:
                        category = map_and_filter_type(type_icon_alt, summary)
                        
                        if category:
                            seen_keys.add(issue_key)
                            raw_issues.append({
                                "issue_key": issue_key,
                                "type": category,
                                "summary": summary,
                                "status": status,
                                "reporter": reporter
                            })

            print(f"📋 Encontrados {len(raw_issues)} chamados pertencentes às 4 categorias. Extraindo respostas e detalhes...")
            for idx, item in enumerate(raw_issues):
                if idx < 50:
                    resp_info = await fetch_issue_response(page, item["issue_key"])
                    item["created_date"] = resp_info["created_date"] or item.get("created_date", "")
                    if resp_info["reporter"]:
                        item["reporter"] = resp_info["reporter"]
                    item["response_author"] = resp_info["response_author"]
                    item["response_date"] = resp_info["response_date"]
                    item["response_text"] = resp_info["response_text"]
                    print(f"   [{idx+1}/{len(raw_issues)}] {item['issue_key']} ({item['type']}) -> Data: {item.get('created_date', 'N/A')} | Solicitante: {item['reporter']}")
                else:
                    item["created_date"] = ""
                    item["response_author"] = ""
                    item["response_date"] = ""
                    item["response_text"] = ""

                extracted_reports.append(item)

            print(f"✅ Sincronização concluída! Total de {len(extracted_reports)} chamados filtrados salvos.")

        except Exception as e:
            print(f"❌ Erro durante a automação: {e}")

        await browser.close()

    if extracted_reports:
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted_reports, f, ensure_ascii=False, indent=2)
        print(f"💾 Dados atualizados em: {JSON_OUTPUT_PATH}")

        if sincronizar_jira_com_sheets:
            try:
                sincronizar_jira_com_sheets()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar o Google Sheets: {e}")

        if sincronizar_jira_com_supabase:
            try:
                sincronizar_jira_com_supabase()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar o Supabase: {e}")

    return extracted_reports

if __name__ == "__main__":
    asyncio.run(sync_jira_reports())
