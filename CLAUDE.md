# BOT_PRINCIPAL — Contexto do Projeto

## O que é

Bot de consulta de saldo FGTS. Lê uma planilha XLSX com CPFs, consulta o saldo de cada um via API do sistema V8, salva os resultados em JSON e permite exportação para Excel.

## Arquivos principais

- `main.py` — ponto de entrada; toda a lógica de autenticação, consulta e simulação
- `export.py` — executado separadamente pelo operador após o bot terminar; converte `result_json/result.json` em Excel
- `logger_setup.py` — configura logging para arquivo em `logs/` (compatível com PyInstaller)
- `VISU.py` — utilitário avulso para inspecionar o JSON gerado (não faz parte do fluxo principal)

## Fluxo de execução

1. `update_env()` carrega ou solicita credenciais (`.env`) — USER_ID, USER_NAME, USER_PASSWORD, USER_TOKEN
2. `bot_auth()` valida o operador na API própria (`railway.app`) usando USER_TOKEN
3. Lê o único arquivo XLSX dentro da pasta `base/`
4. Para cada CPF: `consult_balance()` → `simulation()` → salva em `result_json/result.json`
5. O contador em `contador.txt` guarda o progresso; ao concluir com sucesso é zerado para a próxima execução
6. O operador roda `export.py` separadamente para gerar o Excel final

## APIs externas

| Finalidade | URL |
|---|---|
| Auth token V8 | `https://auth.v8sistema.com/oauth/token` |
| Consulta saldo FGTS | `https://bff.v8sistema.com/fgts/balance` |
| Simulação | `https://bff.v8sistema.com/fgts/simulations` |
| Auth do bot (operador) | `https://web-production-7127e.up.railway.app/users/` |

- O token V8 dura 24h — o bot roda de madrugada e é desligado antes de expirar normalmente
- Em caso de 401 inesperado, `main()` renova o token automaticamente e retenta o CPF

## Status de retorno (`ConsultStatus`)

Enum em `main.py` com os valores possíveis por CPF:

| Status | Significado |
|---|---|
| `NAO AUTORIZADO` | CPF sem autorização na instituição fiduciária |
| `SEM SALDO` | Saldo zerado ou parcelas abaixo de R$10 |
| `CPF INVÁLIDO` | CPF rejeitado pela API |
| `FALHA CONSULTA` | Erro de rede ou resposta inesperada (não é saldo zero) |
| `TOKEN EXPIRADO` | 401 recebido; tratado internamente, não salvo no resultado |
| valor numérico | Saldo disponível em reais |

## Decisões de design

- **`time.sleep(2)` por CPF** — intencional para não estourar rate limit da API V8
- **Processamento sequencial** — não paralelizar; risco de bloqueio pela API
- **Pausa às 5h** — encerra limpo com `return` em vez de loop infinito
- **Distribuição via PyInstaller** — `logger_setup.py` detecta `sys.frozen` para salvar logs junto ao `.exe`
- **Senha em `.env`** — aceitável dado o contexto de uso interno/operacional

## Estrutura de pastas esperada em runtime

```
BOT_PRINCIPAL/
├── base/           # Exatamente um arquivo XLSX com CPFs na coluna A
├── result_json/    # Criado automaticamente; contém result.json
├── logs/           # Criado automaticamente; logs por sessão
├── contador.txt    # Progresso atual (zerado ao concluir)
└── .env            # Credenciais persistidas
```
