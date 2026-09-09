import asyncio
from playwright.async_api import async_playwright
import sys
import os
import json
import datetime
import re

sys.stdout.reconfigure(encoding='utf-8')

JIRA_USER = "ruan.dalson@entregospsumarezinho.com.br"
JIRA_PASS = "Ruankz100%"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_OUTPUT_PATH = os.path.join(BASE_DIR, "jira_reports_data.json")

async def fetch_issue_response(page, issue_key):
    """Navega até o detalhe do chamado e extrai a última resposta/atividade humana"""
    url = f"https://ifood.atlassian.net/helpcenter/entrego/portal/4623/{issue_key}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(1800)

        # Procura elementos de atividade/comentários
        # No Jira Helpcenter, os comentários ficam em divs dentro da seção Atividade
        content = await page.inner_text("body")
        lines = [l.strip() for l in content.split('\n') if l.strip()]

        response_author = ""
        response_date = ""
        response_text = ""

        # Localiza a seção Atividade
        if "Atividade" in lines:
            idx = lines.index("Atividade")
            sub_lines = lines[idx + 1:]
            
            for i in range(len(sub_lines) - 2):
                author = sub_lines[i]
                date_str = sub_lines[i + 1]
                text_candidate = sub_lines[i + 2]

                # Ignora "Resposta automática"
                if author != "Resposta automática" and "O status da sua" not in text_candidate and "Adicionar comentário" not in author:
                    # Verifica se a data parece válida (ex: 01/set/26 16:15)
                    if re.search(r'\d{2}/\w{3}/\d{2}', date_str) or "às" in date_str or ":" in date_str:
                        response_author = author
                        response_date = date_str
                        response_text = text_candidate
                        break

        return {
            "response_author": response_author,
            "response_date": response_date,
            "response_text": response_text
        }
    except Exception as e:
        return {"response_author": "", "response_date": "", "response_text": ""}

async def sync_jira_reports():
    print("=" * 60)
    print(f"🚀 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sincronizando Chamados e Atividades do Jira...")
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

                if current_count == previous_count and current_count > 0:
                    break
                previous_count = current_count

            final_rows = await page.query_selector_all("tbody tr")
            print(f"\n[4/4] Extraindo dados de {len(final_rows)} chamados...")

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
                        seen_keys.add(issue_key)
                        
                        if not type_icon_alt:
                            sum_lower = summary.lower()
                            if "escala" in sum_lower: type_icon_alt = "Sugestão de Escala"
                            elif "promo" in sum_lower or "contest" in sum_lower: type_icon_alt = "Contestação de Promoção"
                            elif "garantido" in sum_lower: type_icon_alt = "Contestação de Garantido FE"
                            elif "erro" in sum_lower or "bug" in sum_lower or "modal" in sum_lower: type_icon_alt = "Problemas Cadastrais"
                            else: type_icon_alt = "Dúvidas Gerais"

                        raw_issues.append({
                            "issue_key": issue_key,
                            "type": type_icon_alt,
                            "summary": summary,
                            "status": status,
                            "reporter": reporter
                        })

            print(f"📋 Extraindo a atividade/resposta dos chamados mais recentes (Abertos e Concluídos)...")
            # Coleta detalhe de resposta para os 40 chamados mais recentes para manter execução ultrarrápida
            for idx, item in enumerate(raw_issues):
                if idx < 50:  # Captura detalhes completos das atividades das 50 issues mais recentes
                    resp_info = await fetch_issue_response(page, item["issue_key"])
                    item["response_author"] = resp_info["response_author"]
                    item["response_date"] = resp_info["response_date"]
                    item["response_text"] = resp_info["response_text"]
                    print(f"   [{idx+1}/50] {item['issue_key']} -> Resposta: '{resp_info['response_text'][:40]}...'" if resp_info['response_text'] else f"   [{idx+1}/50] {item['issue_key']} -> Sem comentário humano")
                else:
                    item["response_author"] = ""
                    item["response_date"] = ""
                    item["response_text"] = ""

                extracted_reports.append(item)

            print(f"✅ Sincronização concluída! {len(extracted_reports)} chamados gravados.")

        except Exception as e:
            print(f"❌ Erro durante a automação: {e}")

        await browser.close()

    if extracted_reports:
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted_reports, f, ensure_ascii=False, indent=2)
        print(f"💾 Dados atualizados em: {JSON_OUTPUT_PATH}")

    return extracted_reports

if __name__ == "__main__":
    asyncio.run(sync_jira_reports())
