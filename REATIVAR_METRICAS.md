# Como Reativar o Módulo de Métricas

Para voltar a ativar a coleta e exibição completa do módulo de Métricas no futuro:

### 1. No arquivo `vercel.json`:
Adicione a build e a rota do script `api/metricas_coleta.py`:

```json
{
  "version": 2,
  "builds": [
    { "src": "api/escalas.py", "use": "@vercel/python", "config": { "maxDuration": 60 } },
    { "src": "api/metricas_coleta.py", "use": "@vercel/python", "config": { "maxDuration": 60 } },
    { "src": "api/pedidos.py", "use": "@vercel/python", "config": { "maxDuration": 60 } },
    { "src": "**", "use": "@vercel/static" }
  ],
  "routes": [
    { "src": "/api/escalas", "dest": "api/escalas.py" },
    { "src": "/api/metricas_coleta", "dest": "api/metricas_coleta.py" },
    { "src": "/api/pedidos", "dest": "api/pedidos.py" },
    { "src": "/(.*)", "dest": "/$1" }
  ]
}
```

### 2. No arquivo `api/metricas_coleta.py`:
Remova o bloco de trava no topo da função `do_GET`:

```python
# Apague estas linhas do do_GET:
self.send_response(200)
self.send_header('Content-type','application/json')
self.end_headers()
self.wfile.write(b'{"status": "disabled", "message": "Coleta de metricas desativada temporariamente."}')
return
```

### 3. No arquivo `index.html`:
Descomente a linha do menu de navegação:

```html
<li><a href="metricas.html" target="_blank" style="color:var(--menta-viva);font-weight:700;">Métricas</a></li>
```
