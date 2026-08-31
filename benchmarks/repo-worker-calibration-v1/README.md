# Repo-Worker Calibration Benchmark (v1)

Benchmark comparativo rigoroso de calibração para tarefas de `repo-worker` entre 8 perfis:
- **B1**: Bonsai thinking OFF / DSpark OFF
- **B2**: Bonsai thinking ON / DSpark OFF
- **B3**: Bonsai thinking OFF / DSpark ON
- **B4**: Bonsai thinking ON / DSpark ON
- **O1**: Ornith 1.5 9B thinking OFF
- **O2**: Ornith 1.5 9B thinking ON
- **Q1**: Qwen3.8-22.62b-v3 Q4_K_M
- **Q2**: Vireqo-27B-Plus

## Arquitetura e Configuração Fixa
- **Contexto**: 32768
- **Concurrency**: 1
- **Flash Attention**: ON
- **Threads / Batch Threads**: 4 / 4
- **KV Cache**: K = Q8_0, V = Q4_0
- **GPU Offload**: Full GPU offload explícito (-ngl 999 para Bonsai, Ornith e Vireqo; -ngl 58 para Qwen3.8-22.62B com margem de segurança de VRAM).

## Protocolo de Ferramentas
- `list`: listagem de diretórios
- `search`: busca de texto/regex via ripgrep
- `read`: leitura de trechos com número de linhas
- `edit`: substituição exata com `old` e `new`
- `patch`: aplicação de unified diff
- `run`: execução de comandos de teste seguros
- `done`: resposta final concisa
