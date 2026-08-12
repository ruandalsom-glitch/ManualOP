import sys
import csv
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append('.')
from api.escalas import Sessao, CONTAS, processar_escalas

def testar_coleta():
    fuso_br = timezone(timedelta(hours=-3))
    now_br = datetime.now(fuso_br)
    
    data_alvo = now_br.strftime("%Y-%m-%d")
    horario_coleta = now_br.strftime("%Y-%m-%d %H:%M")
    
    print(f"Iniciando teste de coleta para {horario_coleta}")
    
    todas_contas_ativas = [c for c in CONTAS if c.get("ativo", True)]
    sessoes = [Sessao(c) for c in todas_contas_ativas]
    
    todos_registros = []
    
    def processar_sessao(sessao):
        registros_sessao = []
        for regiao in sessao.regioes:
            print(f"Coletando para {regiao['nome']} ({sessao.email})...")
            try:
                regs = processar_escalas(sessao, data_alvo, horario_coleta, regiao["nome"])
                registros_sessao.extend(regs)
            except Exception as e:
                print(f"Erro coletar {regiao['nome']}: {str(e)}")
                try:
                    if sessao.renovar_jwt():
                        regs = processar_escalas(sessao, data_alvo, horario_coleta, regiao["nome"])
                        registros_sessao.extend(regs)
                    else:
                        print(f"Falha renovar JWT para {sessao.email}")
                except Exception as e2:
                    print(f"Erro pos-renovacao {regiao['nome']}: {str(e2)}")
        return registros_sessao

    # Executa as coletas nas contas em paralelo
    with ThreadPoolExecutor(max_workers=3) as executor:
        futuros = [executor.submit(processar_sessao, s) for s in sessoes]
        for f in as_completed(futuros):
            try:
                regs = f.result()
                todos_registros.extend(regs)
            except Exception as e:
                print(f"Erro Thread: {str(e)}")
                
    if not todos_registros:
        print("Nenhum registro foi retornado. Verifique se ha turnos ativos agora.")
        return

    nome_arquivo = f"resultado_coleta_{now_br.strftime('%Y%m%d_%H%M%S')}.csv"
    
    colunas = ["regiao", "data", "turno", "praca", "subpraca", "logados", "slots", "pct_logados", "horario_coleta", "modal"]
    
    with open(nome_arquivo, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=colunas, delimiter=';')
        writer.writeheader()
        for r in todos_registros:
            writer.writerow(r)
            
    print(f"\nColeta concluida! {len(todos_registros)} registros salvos em: {nome_arquivo}")

if __name__ == "__main__":
    testar_coleta()
