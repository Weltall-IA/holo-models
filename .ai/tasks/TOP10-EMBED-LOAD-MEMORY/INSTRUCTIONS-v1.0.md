# INSTRUCTIONS v1.0 — memória de carregamento dos embeddings líderes

## Objetivo

Medir, de forma curta e isolada, o custo de carregamento dos embeddings que representam o top 10 atual do benchmark Holo.

Esta rodada NÃO mede qualidade, NÃO executa corpus completo, NÃO gera candidates e NÃO carrega reranker.

O resultado deve responder, para cada peso local único:

- nome completo e quantidade declarada de parâmetros;
- arquivo ou conjunto de arquivos de pesos usado;
- bytes exatos em disco;
- MB decimais e MiB binários em disco;
- RAM do sistema antes do carregamento;
- RAM do processo em idle após carregamento estabilizado;
- delta de RAM atribuível ao processo;
- VRAM antes do carregamento;
- VRAM do processo em idle após carregamento estabilizado;
- delta de VRAM atribuível ao processo;
- pico de RAM durante carregamento;
- pico de VRAM durante carregamento;
- tempo de carregamento;
- backend e versão;
- comando executado;
- status do smoke mínimo;
- motivo exato quando a medição não for possível.

## Repositório e branch

- Repositório: `Weltall-IA/holo-models`
- Branch: `bench/top10-embedding-load-memory`
- Base: `agent/prepare-next-embedding-rerank-batch-v2`

Antes de qualquer alteração, confirme:

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light

git remote get-url origin
git branch --show-current
git status --short
git rev-parse HEAD

git fetch origin --prune
git switch bench/top10-embedding-load-memory
git pull --ff-only origin bench/top10-embedding-load-memory
```

O remote deve corresponder a `Weltall-IA/holo-models`.

Não use `reset --hard`, `clean`, stash automático, force-push ou remoção de arquivos não rastreados.

Preserve integralmente, se ainda existirem:

- `rerank/`;
- `runtimes/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`;
6. esta instrução.

## Escopo dos modelos

Resolva o top 10 atual a partir de `published_pipelines_ranked_by_mrr_at_10`, mas deduplique por peso local real.

O conjunto esperado inclui os seguintes embeddings/perfis relevantes:

1. `qwen3_embedding_4b_q8_0`;
2. `nomic_embed_text_v2_moe_q4`;
3. `nemotron_3_embed_1b_nvfp4`;
4. `nemotron_8b_abiray_q4_audit_1024` e `nemotron_8b_abiray_q4_audit_4096`, medidos uma única vez porque usam o mesmo GGUF;
5. `colibri_ptbr`;
6. `embeddinggemma` e `embeddinggemma_768_float32`, medidos uma única vez quando a identidade do peso for comprovadamente a mesma;
7. `voyage_4_large_1024_float32`;
8. demais variantes Voyage que entrarem no top 10 por melhor pipeline, quando aplicável.

Regras:

- Não carregue o mesmo arquivo de peso duas vezes apenas porque há duas dimensões ou dois IDs históricos.
- Para modelos Voyage/API, não tente baixar ou reconstruir pesos proprietários. Registre `REMOTE_API_NO_LOCAL_LOAD`, parâmetros/tamanho local como não publicados ou não aplicáveis e consumo local de modelo como `0`, distinguindo isso de consumo do cliente HTTP.
- Não substitua um artefato por outro parecido.
- Não baixe pesos novos sem necessidade. Use somente pesos já existentes e verificados no host.
- Se um peso local esperado não estiver disponível, registre `BLOCKED_MISSING_LOCAL_WEIGHT` com caminho esperado e evidência da busca.

## Implementação

Crie um runner canônico e reutilizável em:

`benchmark/embedding-v3/holo_benchmark/embedding_load_memory.py`

Crie testes em:

`benchmark/embedding-v3/tests/test_embedding_load_memory.py`

O runner deve:

1. executar um modelo por processo isolado;
2. garantir ausência de reranker e de outro servidor de embedding usando GPU antes de cada medição;
3. registrar baseline de RAM e VRAM imediatamente antes do processo;
4. iniciar o runtime correto para o formato real do peso;
5. esperar o modelo ficar pronto e estabilizar por pelo menos 5 segundos;
6. executar apenas um smoke mínimo de uma consulta curta e um documento curto, suficiente para provar que o modelo está funcional;
7. amostrar RAM e VRAM durante o carregamento em intervalo de no máximo 250 ms;
8. registrar idle estabilizado e pico;
9. encerrar o processo graciosamente;
10. confirmar liberação de RAM/VRAM antes do modelo seguinte;
11. nunca manter dois modelos carregados simultaneamente.

### Medição de RAM

Use dados do processo e de seus filhos, não apenas memória livre global.

Registre, em bytes e MiB:

- RSS do processo principal;
- soma de RSS da árvore de processos;
- pico da árvore de processos;
- baseline global apenas como contexto.

Quando PSS estiver disponível de forma confiável, registre também PSS, mas não a torne obrigatória.

### Medição de VRAM

Use `nvidia-smi` ou NVML para identificar o consumo por PID.

Registre, em bytes e MiB:

- VRAM por PID da árvore;
- soma estabilizada;
- pico durante carregamento;
- baseline global antes do início.

Não calcule VRAM do modelo apenas pelo tamanho do arquivo.

### Tamanho do modelo

Para cada modelo local, registre:

- todos os arquivos de peso efetivamente necessários;
- bytes exatos por arquivo;
- soma total em bytes;
- MB decimal: `bytes / 1_000_000`;
- MiB binário: `bytes / 1_048_576`;
- SHA-256 de cada peso;
- quantização/dtype.

Não confunda parâmetros, tamanho em disco, RAM e VRAM.

## Saídas

Grave o artefato canônico em:

`benchmark/embedding-v3/results/load-memory/top10_embedding_load_memory.json`

Gere também o relatório humano:

`benchmark/embedding-v3/TOP10_EMBEDDING_LOAD_MEMORY_REPORT.md`

O JSON deve conter:

- `schema_version`;
- timestamp UTC;
- hardware;
- versão de CUDA/driver;
- metodologia;
- lista original das 10 posições do ranking;
- mapa de deduplicação entre IDs e pesos reais;
- resultados por peso local único;
- entradas remotas/API separadas;
- falhas ou bloqueios reais;
- tabela ordenada pelo melhor MRR@10 associado ao embedding.

O Markdown deve mostrar claramente:

| Ranking | Embedding completo | Parâmetros | Quantização | Tamanho MB | Tamanho MiB | RAM idle MiB | RAM pico MiB | VRAM idle MiB | VRAM pico MiB | Load s | Status |

Não inclua reranker na tabela nem no processo de medição.

## Critérios de validade

A medição só é válida quando:

- o modelo foi carregado sozinho;
- o smoke mínimo passou;
- o PID e seus filhos foram identificados;
- RAM e VRAM foram amostradas durante todo o carregamento;
- o processo foi encerrado e a memória foi liberada;
- tamanho e hash do peso correspondem ao artefato esperado;
- nenhuma API paga foi chamada;
- nenhum reranker foi iniciado.

Se um runtime reportar memória reservada que não pode ser atribuída com precisão, registre separadamente `allocated`, `reserved` e consumo observado pelo driver, sem escolher arbitrariamente um deles.

## Validação

Execute:

```bash
python -m unittest benchmark.embedding-v3.tests.test_embedding_load_memory -v
python -m unittest discover -s benchmark/embedding-v3/tests -v
python .ai/validate_governance.py
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Revise o diff completo.

## Git e PR

Inclua somente arquivos desta rodada.

Mensagem de commit sugerida:

`Measure isolated load memory for top embedding models`

Faça push da branch e abra PR contra:

`agent/prepare-next-embedding-rerank-batch-v2`

O PR deve permanecer draft até:

- todos os pesos locais disponíveis serem medidos;
- bloqueios reais estarem documentados;
- testes e validações passarem;
- o relatório final conter MB/MiB, RAM e VRAM sem estimativas indevidas.

Não faça merge.

## Retorno obrigatório

Informe:

1. HEAD inicial e final;
2. lista original das 10 posições;
3. pesos locais únicos realmente medidos;
4. mapa de IDs duplicados para o mesmo peso;
5. tabela completa com parâmetros, MB, MiB, RAM idle/pico, VRAM idle/pico e load time;
6. modelos API/remotos e por que não possuem carga local;
7. bloqueios;
8. testes e validações;
9. arquivos alterados;
10. commit, push e PR;
11. confirmação de que nenhum reranker e nenhuma API paga foram usados.

Frase final:

`v1.0 — memória isolada de carregamento dos embeddings líderes medida sem reranker.`
