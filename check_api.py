import sys
import json
from datetime import datetime, timezone, timedelta
sys.path.append('.')
from api.escalas import Sessao, CONTAS

fuso_br = timezone(timedelta(hours=-3))
data_alvo = datetime.now(fuso_br).strftime("%Y-%m-%d")

# Use the first active account
conta = next(c for c in CONTAS if c["ativo"])
sessao = Sessao(conta)

# Fetch scales
dados = sessao.buscar_pagina_escalas(1, data_alvo, data_alvo)
registros = dados.get("values", [])

if registros:
    print("KEYS OF RECORD:")
    print(list(registros[0].keys()))
    print("SHIFT:")
    print(json.dumps(registros[0].get("shift", {}), indent=2))
else:
    print("Nenhum registro encontrado")
