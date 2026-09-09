import asyncio
from playwright.async_api import async_playwright
import sys
import os
import json
import datetime
import requests

# Forçar encoding UTF-8 no console do Windows
sys.stdout.reconfigure(encoding='utf-8')

JIRA_USER = "ruan.dalson@entregospsumarezinho.com.br"
JIRA_PASS = "Ruankz100%"

# Caminho para salvar a base leve de relatórios JSON (para consumo ultrarrápido sem gasto de Egress)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_OUTPUT_PATH = os.path.join(BASE_DIR, "jira_reports_data.json")

# Configuração do Supabase (Opcional se tabela configurada)
SUPABASE_URL = "https://wpuyanodymsjzsqzbmfy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwdXlhbm9keW1zanpzcXpibWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEyMzg2ODIsImV4cCI6MjA1NjzgNDY4Mn0.g-pY6d..._demo"

async def sync_jira_reports():
    print("=" * 60)
    print(f"🚀 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando Sincronizacao de Chamados Jira...")
    print("=" * 60)

    extracted_reports = []

    async with async_playwright() as p:
        # Execução 100% invisível em segundo plano (Headless)
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

            # Clique em Continue with password
            pass_btn = await page.query_selector("button:has-text('Continue with password'), button:has-text('Continuar com senha')")
            if pass_btn:
                await pass_btn.click()
                await page.wait_for_timeout(2500)

            # Preenchimento de Senha
            pass_input = await page.query_selector("input[type='password'], #password")
            if pass_input:
                await pass_input.fill(JIRA_PASS)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(6000)

            print("[3/4] Coletando lista de chamados no Helpcenter EntreGô...")
            all_requests_url = "https://ifood.atlassian.net/helpcenter/entrego/user/requests?reporter=all&statuses=open,closed"
            await page.goto(all_requests_url)
            await page.wait_for_timeout(4000)

            # Extração dos dados da tabela
            rows = await page.query_selector_all("tbody tr")
            print(f"   -> Encontrados {len(rows)} chamados no portal.")

            for r in rows:
                text = await r.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                
                # Tenta capturar o link direto do chamado
                link_elem = await r.query_selector("a")
                link_href = await link_elem.get_attribute("href") if link_elem else None
                full_link = f"https://ifood.atlassian.net{link_href}" if link_href and link_href.startswith("/") else link_href

                if len(lines) >= 4:
                    # Estrutura típica da tabela: [Tipo/Ref, Resumo, Status, Projeto, Solicitante]
                    issue_key = ""
                    summary = ""
                    status = ""
                    reporter = ""

                    for idx, line in enumerate(lines):
                        if "SMENTGO-" in line:
                            issue_key = line
                            if idx + 1 < len(lines): summary = lines[idx + 1]
                            if idx + 2 < len(lines): status = lines[idx + 2]
                            if len(lines) > 4: reporter = lines[-1]
                            break

                    if not issue_key and len(lines) >= 4:
                        issue_key = lines[0]
                        summary = lines[1]
                        status = lines[2]
                        reporter = lines[-1]

                    if issue_key:
                        extracted_reports.append({
                            "issue_key": issue_key,
                            "summary": summary,
                            "status": status,
                            "reporter": reporter,
                            "url": full_link or f"https://ifood.atlassian.net/helpcenter/entrego/portal/4623/{issue_key}",
                            "updated_at": datetime.datetime.now().isoformat()
                        })

            print(f"✅ [4/4] Coleta concluida com sucesso! {len(extracted_reports)} chamados processados.")

        except Exception as e:
            print(f"❌ Erro durante a automacao: {e}")

        await browser.close()

    # Salva os relatórios no arquivo JSON estático para carregamento ultra rápido na web (0 bytes egress!)
    if extracted_reports:
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted_reports, f, ensure_ascii=False, indent=2)
        print(f"💾 Dados salvos localmente em: {JSON_OUTPUT_PATH}")

    return extracted_reports

if __name__ == "__main__":
    asyncio.run(sync_jira_reports())
