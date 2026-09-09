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

            print("   -> Executando rolagem dinâmica para carregar 100% do histórico...")
            previous_count = 0
            max_scrolls = 35
            
            for scroll_idx in range(max_scrolls):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1200)

                current_rows = await page.query_selector_all("tbody tr")
                current_count = len(current_rows)
                print(f"      Scroll #{scroll_idx + 1}: {current_count} chamados carregados...")

                if current_count == previous_count and current_count > 0:
                    print("   -> Fim do histórico atingido.")
                    break
                previous_count = current_count

            final_rows = await page.query_selector_all("tbody tr")
            print(f"\n[4/4] Extraindo tipos, resumos, status e solicitantes de {len(final_rows)} chamados...")

            seen_keys = set()
            for r in final_rows:
                text = await r.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]

                # Tenta capturar a tag de tipo/ícone (ex: img ou svg no primeiro td)
                first_td = await r.query_selector("td:first-child")
                type_icon_alt = ""
                if first_td:
                    img = await first_td.query_selector("img")
                    if img:
                        type_icon_alt = await img.get_attribute("alt") or await img.get_attribute("title") or ""
                    if not type_icon_alt:
                        svg = await first_td.query_selector("svg")
                        if svg:
                            type_icon_alt = await svg.get_attribute("aria-label") or await svg.get_attribute("title") or ""

                if len(lines) >= 3:
                    issue_key = ""
                    summary = ""
                    status = ""
                    reporter = ""
                    issue_type = type_icon_alt

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

                    # Deduz o tipo do chamado se não capturado pelo ícone
                    if not issue_type:
                        sum_lower = summary.lower()
                        if "escala" in sum_lower:
                            issue_type = "Escala"
                        elif "promo" in sum_lower or "contest" in sum_lower:
                            issue_type = "Promoção"
                        elif "erro" in sum_lower or "bug" in sum_lower or "falha" in sum_lower or "modal" in sum_lower:
                            issue_type = "Problema / Bug"
                        else:
                            issue_type = "Geral"

                    if issue_key and issue_key not in seen_keys:
                        seen_keys.add(issue_key)
                        extracted_reports.append({
                            "issue_key": issue_key,
                            "type": issue_type,
                            "summary": summary,
                            "status": status,
                            "reporter": reporter,
                            "updated_at": datetime.datetime.now().isoformat()
                        })

            print(f"✅ Extração concluída! {len(extracted_reports)} chamados salvos com tipos e solicitantes.")

        except Exception as e:
            print(f"❌ Erro durante a automação: {e}")

        await browser.close()

    if extracted_reports:
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted_reports, f, ensure_ascii=False, indent=2)
        print(f"💾 Dados salvos em: {JSON_OUTPUT_PATH}")

    return extracted_reports

if __name__ == "__main__":
    asyncio.run(sync_jira_reports())
