import asyncio
from playwright.async_api import async_playwright
import sys
import os
import json
import datetime

# Forçar encoding UTF-8 no console do Windows
sys.stdout.reconfigure(encoding='utf-8')

JIRA_USER = "ruan.dalson@entregospsumarezinho.com.br"
JIRA_PASS = "Ruankz100%"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_OUTPUT_PATH = os.path.join(BASE_DIR, "jira_reports_data.json")

async def sync_jira_reports():
    print("=" * 60)
    print(f"🚀 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando Sincronizacao Completa dos Chamados Jira...")
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

            print("[3/4] Acessando todos os chamados no Helpcenter EntreGô...")
            all_requests_url = "https://ifood.atlassian.net/helpcenter/entrego/user/requests?reporter=all&statuses=open,closed"
            await page.goto(all_requests_url)
            await page.wait_for_timeout(4000)

            # Rolagem Dinâmica para carregar 100% dos chamados da lista
            print("   -> Executando rolagem dinâmica para carregar 100% do histórico de chamados...")
            previous_count = 0
            max_scrolls = 30  # Garante buscar centenas de registros se houver
            
            for scroll_idx in range(max_scrolls):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1200)

                current_rows = await page.query_selector_all("tbody tr")
                current_count = len(current_rows)
                print(f"      Scroll #{scroll_idx + 1}: {current_count} chamados carregados...")

                if current_count == previous_count and current_count > 0:
                    print("   -> Fim do histórico atingido. Todos os chamados foram carregados.")
                    break
                previous_count = current_count

            # Extração limpa (sem links externos, puramente indicativos)
            final_rows = await page.query_selector_all("tbody tr")
            print(f"\n[4/4] Processando dados limpos de {len(final_rows)} chamados...")

            seen_keys = set()
            for r in final_rows:
                text = await r.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]

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

                    if not issue_key and len(lines) >= 3:
                        issue_key = lines[0]
                        summary = lines[1]
                        status = lines[2]
                        reporter = lines[-1]

                    if issue_key and issue_key not in seen_keys:
                        seen_keys.add(issue_key)
                        extracted_reports.append({
                            "issue_key": issue_key,
                            "summary": summary,
                            "status": status,
                            "reporter": reporter,
                            "updated_at": datetime.datetime.now().isoformat()
                        })

            print(f"✅ Extração concluída com sucesso! Total de {len(extracted_reports)} chamados únicos salvos.")

        except Exception as e:
            print(f"❌ Erro durante a automação: {e}")

        await browser.close()

    # Salva no arquivo JSON estático para exibição ultra rápida na web
    if extracted_reports:
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted_reports, f, ensure_ascii=False, indent=2)
        print(f"💾 Dados atualizados em: {JSON_OUTPUT_PATH}")

    return extracted_reports

if __name__ == "__main__":
    asyncio.run(sync_jira_reports())
