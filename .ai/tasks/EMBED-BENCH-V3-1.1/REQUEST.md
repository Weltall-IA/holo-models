# Benchmark de embeddings e reranking v3

```yaml
task_id: EMBED-BENCH-V3-1.1
mode: dual
branch: ai/embedding-benchmark-v3
commit_base: 57cbc6059ad8a15ebf2eb81adb402a5dd2373cd0
author: autor-remoto
allow_local_project_edits: true
```

## Objetivo

Preparar e executar somente os Gates 0 e 1 do benchmark de embeddings e reranking do Projeto Holo, sem alterar `infra-holoplay`, sem baixar checkpoints completos e sem chamar a Voyage API.

## Escopo permitido

Conteúdo versionado:

- `benchmark/embedding-v3/**`;
- `.ai/tasks/EMBED-BENCH-V3-1.1/EXECUTION.md`;
- `.ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml`.

Runtime local ignorado pelo Git:

- `benchmarks/holo-embedding-benchmark-v3/**`;
- caches temporários da `.venv`;
- nenhum peso no Gate 0 ou Gate 1.

## Autorização local

```yaml
allow_local_project_edits: true
allowed_local_edit_paths:
  - benchmark/embedding-v3/environment.json
  - benchmark/embedding-v3/system_info.json
  - benchmark/embedding-v3/requirements-resolved.txt
  - benchmark/embedding-v3/GATE_0_REPORT.md
  - benchmark/embedding-v3/GATE_1_REPORT.md
  - benchmark/embedding-v3/DIRECTOR_BRIEF.md
  - benchmark/embedding-v3/gate_status.json
  - benchmark/embedding-v3/data/holo_fake_scenes_v3/corpus.jsonl
  - benchmark/embedding-v3/data/holo_fake_scenes_v3/queries.jsonl
  - benchmark/embedding-v3/data/holo_fake_scenes_v3/validation.json
  - benchmark/embedding-v3/data/holo_fake_scenes_v3/semantic_review_checklist.json
  - benchmark/embedding-v3/data/holo_fake_scenes_v3/semantic_review.json
  - benchmark/embedding-v3/data/holo_fake_scenes_v3/hashes.json
  - .ai/tasks/EMBED-BENCH-V3-1.1/EXECUTION.md
  - .ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml
allowed_runtime_write_paths:
  - benchmarks/holo-embedding-benchmark-v3/**
```

A autorização permite apenas executar coletores e geradores versionados e preencher a revisão semântica no schema fornecido. Não permite redigir ou adaptar código, corpus, prompts, metodologia ou regras.

## Gate 0

- confirmar checkout, branch, HEAD, `origin/master` e working tree;
- criar `.venv` isolada com Python 3.11, salvo incompatibilidade comprovada;
- instalar dependências autorizadas;
- inventariar CPU, RAM, GPU, VRAM, driver, CUDA, kernel, Python, filesystem, espaço e bibliotecas;
- validar CUDA no PyTorch e uma alocação mínima;
- produzir manifesto e dry-run;
- não baixar pesos nem chamar APIs.

## Gate 1

- gerar deterministamente 30 obras, 600 chunks e 150 consultas;
- validar schema, IDs, referências, timestamps, tokens, duplicações, vazamento lexical e negativos difíceis;
- revisar semanticamente pelo menos 30 consultas, com cobertura de todas as categorias;
- qualquer rejeição interrompe o congelamento e exige nova versão autorizada;
- congelar corpus com SHA-256;
- não executar embeddings.

## Critérios de aceitação

- Gate 0 com evidência real do PC local ou bloqueio honesto;
- Gate 1 com contagens e distribuição exatas;
- zero consulta sem relevante;
- zero ID ou consulta duplicada;
- chunks entre 180 e 420 tokens estimados, máximo rígido de 512;
- corpus em português brasileiro e inteiramente fictício;
- hashes reproduzíveis;
- nenhuma alteração no `infra-holoplay`;
- nenhuma chamada Voyage;
- nenhum checkpoint completo baixado;
- parada obrigatória após Gate 1.

## Fora do escopo

- Gates 2 a 6;
- integração ao Holo;
- banco real;
- Qdrant ou PostgreSQL;
- alteração de driver, CUDA do sistema ou serviços;
- `ollama create`, reflink ou remoção de modelo;
- merge ou publicação.

## Entrega

Atualize `EXECUTION.md` e `STATUS.yml`, publique somente os arquivos autorizados na mesma branch e devolva o turno ao autor remoto.
