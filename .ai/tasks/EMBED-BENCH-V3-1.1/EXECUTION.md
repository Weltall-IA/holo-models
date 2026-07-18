# EXECUTION.md — EMBED-BENCH-V3-1.1

## Identificação

- **Tarefa**: EMBED-BENCH-V3-1.1
- **Branch**: `ai/embedding-benchmark-v3`
- **SHA executado**: `9830a832ebfab148c86ccb3662c5d9e05a821dd5`
- **origin/master**: `9e22f36d690e9cae5c27ca0e60fe4fd4858edf84`
- **Payload HEAD confirmado**: `e2df11b13f3ffd6c0d3211452dd6758cf6e821d5` (ancestral)
- **Modo**: `dual`
- **Turno**: `executor-local`

## Ambiente

- **Sistema**: CachyOS
- **Kernel**: `7.1.3-2-cachyos`
- **CPU**: AMD Ryzen 7 2700X (8 físicos / 16 lógicos)
- **RAM**: 33.566.244.864 bytes
- **GPU**: NVIDIA GeForce RTX 5060 Ti (16 GB VRAM)
- **Driver NVIDIA**: `nvidia-smi` reconhecido
- **CUDA PyTorch**: não disponível (torch não instalado - fora do escopo do Gate 0)
- **Filesystem**: bcachefs UUID `af4831e9`
- **Espaço livre**: ~1,85 TB

## Python

- **Python 3.11**: ausente no sistema
- **Python utilizado**: 3.12.13
- **Interpretador**: `benchmarks/holo-embedding-benchmark-v3/.venv/bin/python`
- **Pacotes instalados (requirements-gate01.txt)**: psutil, pydantic, orjson, rich, pynvml (13 dependências totais)

## Testes

### Compilação (`python -m compileall -q .`)
- **Saída**: 0
- **Status**: PASS

### Testes unitários (`python -m unittest discover -s tests -v`)
9 testes executados, 9 aprovados:
1. `test_counts_and_distribution` — OK
2. `test_review_checklist` — OK
3. `test_token_and_template_limits` — OK
4. `test_unique_queries_and_chunks` — OK
5. `test_local_directory_name_does_not_define_repository_identity` — OK
6. `test_normalizes_https_and_ssh_origins` — OK
7. `test_tracked_changes_still_block_gate` — OK
8. `test_untracked_residue_is_informational` — OK
9. `test_wrong_origin_blocks_gate` — OK
- **Status**: PASS

## Gate 0

### Dry-run (`python benchmark.py --gate 0 --dry-run --skip-api`)
- **Saída**: 0
- **Duração**: 207ms
- **Status**: PASS

### Execução real (`python benchmark.py --gate 0 --skip-api`)
- **Saída**: 0
- **Duração**: 189ms
- **Status**: PASS

### Artefatos gerados
- `benchmark/embedding-v3/environment.json` (3583 bytes)
- `benchmark/embedding-v3/system_info.json` (3503 bytes)
- `benchmark/embedding-v3/requirements-resolved.txt` (74 bytes)
- `benchmark/embedding-v3/GATE_0_REPORT.md` (1020 bytes)
- `benchmark/embedding-v3/gate_status.json` (155 bytes)

## Gate 1

### Primeira execução (`python benchmark.py --gate 1 --skip-api`)
- **Saída**: 3 (corpus candidato gerado, aguardando revisão semântica)
- **Duração**: 699ms

### Revisão semântica
- 35 itens revisados, 35 aprovados
- Nenhuma rejeição
- Schema: `semantic_review.json` versão `1.0`

### Retomada e congelamento (`python benchmark.py --gate 1 --resume --skip-api`)
- **Saída**: 0
- **Duração**: 608ms
- **Status**: PASS

### Artefatos gerados
- `data/holo_fake_scenes_v3/corpus.jsonl` (1.380.943 bytes, 30 obras, 600 chunks)
- `data/holo_fake_scenes_v3/queries.jsonl` (80.961 bytes, 150 consultas)
- `data/holo_fake_scenes_v3/validation.json` (794 bytes)
- `data/holo_fake_scenes_v3/semantic_review_checklist.json` (265.413 bytes)
- `data/holo_fake_scenes_v3/semantic_review.json` (10.300 bytes, 35 aprovados)
- `data/holo_fake_scenes_v3/hashes.json` (1.043 bytes)
- `GATE_1_REPORT.md` (543 bytes)
- `DIRECTOR_BRIEF.md` (351 bytes)

### Hash conjunto
```
combined_sha256: 8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b
```

### Validação
- 30 obras fictícias: PASS
- 600 chunks: PASS
- 150 consultas: PASS
- Zero consulta sem relevante: PASS
- Zero ID duplicado: PASS
- Distribuição exata das categorias: PASS
- Negativos difíceis válidos: PASS
- Corpus inteiramente fictício: PASS
- Token limits (180–420, máx 512): PASS
- Português brasileiro: PASS

## Resíduos preservados

Artefatos da tentativa anterior foram movidos para `benchmarks/holo-embedding-benchmark-v3/previous-failed-run/`:
- `GATE_0_REPORT.md`
- `environment.json`
- `gate_status.json`
- `requirements-resolved.txt`
- `system_info.json`

## Erros e riscos

- Python 3.11 não disponível. Utilizado Python 3.12.13 sem incompatibilidade comprovada.
- `runtime/vane-native-ops/` permanece como resíduo não rastreado (ignorado pelo .gitignore, não bloqueia).
- Nenhum checkpoint baixado, nenhuma chamada Voyage, nenhum embedding executado.
- Gates 2 a 6 bloqueados conforme implementação.

## Responsável

Próximo turno: `autor-remoto`
