# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.12.2

## Objetivo

Auditar por que os dois pesos Nemotron 8B distintos produziram resultados numericamente idênticos por dimensão na v2.2.12.1. Esta etapa não executa novos benchmarks, não chama Voyage, não altera resultados existentes e não consolida o lote.

## Estado obrigatório

- repositório: `Weltall-IA/holo-models`
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- branch: `exec/embed-rerank-batch2-light`
- PR: `#20`, aberto e draft
- HEAD inicial: SHA completo informado no handoff
- nenhum merge autorizado

Leia as regras aplicáveis do repositório antes da execução.

Preserve os não rastreados existentes:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Não use reset, clean, stash automático, checkout destrutivo ou force-push.

## Fatos já medidos

Pesos:

- Abiray: `Abiray/Nemotron-3-Embed-8B-GGUF`, revisão `1ffb81e403311c4dc6879b9c3cbb6ebfa18b86df`, 4.896.390.039 bytes, SHA-256 `a2aa29c618da6eed10d9474e72e33188c61e5fd700aed2fe9a1d98abdc90c6fc`.
- Aqua00: `Aqua00/Nemotron-3-Embed-8B-GGUF`, revisão `fa8f1317579eee6ecfa0a5623f4df0c0d19f5a87`, 4.896.389.984 bytes, SHA-256 `1352d929879c61fccf76ff855c6250c7fdc924479932918febcc6fe384cb70a7`.

Os resultados Abiray e Aqua00 são exatamente iguais em cada dimensão, inclusive métricas raw e pipelines Qwen. Isso não deve ser tratado como erro nem como sucesso conclusivo sem auditoria estrutural dos GGUF e dos candidates.

## Responsabilidade da IA executora

A IA local pode somente:

- inspecionar os dois GGUF locais;
- executar ferramentas somente leitura do llama.cpp ou utilitários Python já instalados;
- comparar metadados, arquitetura e tensores;
- calcular hashes dos candidates e rankings;
- executar testes existentes;
- gerar um único artefato de auditoria autorizado;
- commitar e fazer push desse artefato.

A IA local não pode:

- editar código, testes, configuração, README, consolidado ou resultados;
- executar embeddings ou rerankers novamente;
- chamar APIs;
- baixar modelos ou pacotes;
- alterar ou apagar pesos;
- fazer merge.

## 1. Confirmar caminhos e identidade

Localize os dois arquivos exatos já usados na v2.2.12.1 e confirme novamente:

- caminho;
- tamanho;
- SHA-256;
- repositório e revisão registrados nos quatro resultados raw.

Pare se qualquer valor divergir.

## 2. Comparação GGUF estrutural

Use ferramentas somente leitura disponíveis, preferencialmente `llama-gguf-info`, `llama-gguf` ou parser Python GGUF já instalado. Não instale nada.

Para cada GGUF, extraia e normalize:

- todos os metadados GGUF, excluindo somente campos evidentemente não semânticos como nome do quantizador, URL, descrição e timestamp;
- arquitetura;
- número de tensores;
- nomes dos tensores;
- shapes;
- tipos GGML;
- offsets e tamanhos;
- tokenizer e tokens especiais;
- parâmetros de embedding relevantes.

Calcule:

1. hash do manifesto completo de tensores: nome + shape + tipo + tamanho;
2. hash do conteúdo de cada tensor, quando a ferramenta disponível permitir leitura sem carregar o modelo inteiro em RAM;
3. hash agregado ordenado dos hashes dos tensores;
4. lista exata dos metadados divergentes;
5. lista exata de tensores divergentes.

Não considere diferença de 55 bytes prova de diferença nos tensores. Determine se:

- os tensores são byte a byte idênticos e apenas metadados divergem;
- os tensores diferem, mas as diferenças não alteraram os rankings no corpus;
- a ferramenta disponível não consegue provar a identidade dos tensores.

## 3. Comparação dos candidates

Compare os quatro pares correspondentes:

- Abiray 4096 × Aqua00 4096;
- Abiray 1024 × Aqua00 1024.

Para cada arquivo:

- confirme 150 consultas e top 50;
- calcule SHA-256 do arquivo completo;
- normalize para uma sequência canônica de `query_id` + IDs ordenados dos candidates e calcule SHA-256;
- compare consulta por consulta;
- conte quantas consultas têm ranking diferente;
- quando houver diferença, registre primeira posição divergente e número total de posições divergentes.

Também compare os quatro pipelines Qwen por conteúdo semântico:

- métricas base;
- métricas reranqueadas;
- rankings por consulta;
- rescue/damage;
- normalize removendo apenas IDs, timestamps e proveniência e calcule hash semântico.

## 4. Artefato autorizado

Crie exclusivamente:

`benchmark/embedding-v3/results/reranker/nemotron_8b_abiray_aqua00_identity_audit.json`

O artefato deve conter:

- `schema_version`;
- `status`;
- identidade completa dos dois pesos;
- comandos e ferramentas usados;
- versões das ferramentas;
- hashes de manifestos e tensores;
- diferenças de metadados;
- diferenças de tensores;
- hashes completos e semânticos dos candidates;
- contagem de consultas e posições divergentes;
- hashes semânticos dos pipelines;
- conclusão estritamente factual.

Valores permitidos para `status`:

- `IDENTICAL_TENSORS_METADATA_ONLY_DIFFERENCE`;
- `DISTINCT_TENSORS_IDENTICAL_RANKINGS_ON_CORPUS`;
- `DISTINCT_TENSORS_DISTINCT_RANKINGS`;
- `BLOCKED_TENSOR_IDENTITY_UNPROVEN`.

O payload deve passar `assert_portable_payload`.

## 5. Validação

Execute:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python

"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -p 'test_*.py' -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
"$PYTHON" benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Confirme que:

- somente o artefato de auditoria foi criado;
- todos os 13 artefatos da v2.2.12.1 permanecem byte a byte idênticos;
- `ALL_BENCHMARK_RESULTS.json` e `README.md` permanecem idênticos;
- nenhum arquivo antigo foi alterado;
- nenhum servidor permaneceu ativo.

## 6. Commit e retorno

Faça commit somente se o artefato de auditoria estiver completo e portátil. Faça push sem force.

Retorne:

- HEAD inicial e final completos;
- status da auditoria;
- identidade dos dois pesos;
- hashes dos manifestos e tensores;
- diferenças de metadados e tensores;
- hashes semânticos dos candidates;
- número de consultas e posições divergentes em 4096 e 1024;
- hashes semânticos dos pipelines;
- testes e exit codes;
- arquivo único commitado;
- confirmação de ausência de benchmark, API, download, edição de código e merge.

Não declare o lote concluído. A decisão sobre consolidação e Voyage permanece com o gerente.