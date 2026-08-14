# AGENTS.md — Workspace models (Playstoria)

## Regra: uso de MCPs

- **Sempre que a tarefa envolver um domínio coberto por um MCP disponível, use o MCP em vez de alternativas ad-hoc** (curl manual, scripts avulsos, aproximações) — a menos que o MCP não exista para o caso.
- MCPs configurados neste workspace:

| Domínio | MCP |
|---|---|
| GitHub (repos, PRs, issues, code search) | `github` |
| Documentação de bibliotecas/frameworks | `context7` |
| Banco de dados Postgres | `postgres-mcp-pro` |
| Erros/monitoramento | `sentry` |
| Automação de workflows | `n8n-mcp` |
| Navegador/UI/web | `playwright` |
| Notebooks Jupyter | `jupyter` |
| PHP/Laravel (artisan) | `laravel-boost` |
| Observabilidade cloud | `grafana-cloud-mcp` |

- Prefira MCP para: leitura de issues/PRs (github), consultas SQL (postgres-mcp-pro), documentação oficial de libs (context7), inspeção de erros (sentry), testes de UI (playwright).
- MCPs são read-only por padrão nesta máquina, exceto onde explicitamente permitido; não contorne restrições com bash para replicar o que o MCP faz.
- Preferências explícitas de agentes específicos prevalecem sobre esta regra (ex.: o agente `data` prefere ferramentas nativas de notebook em vez de MCP de notebook).
