# Benchmark decisório de embeddings e rerankers — v1.5

## Objetivo

Comparar pipelines de busca de cenas no corpus congelado `holo_fake_scenes_v3`, separando recuperação vetorial, reranking, qualidade, latência, consumo local e uso de API.

Corpus obrigatório:

- 600 documentos;
- 150 consultas;
- SHA-256 `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`.

## Variantes de embedding

1. `embeddinggemma_768_float32`;
2. `voyage4_nano_1024_float32`;
3. `voyage4_nano_2048_float32`;
4. `voyage4_nano_2048_int8`;
5. `voyage_4_large_1024_float32`.

O Voyage 4 Large reutiliza exclusivamente os checkpoints locais já produzidos. O runner não chama a API de embedding para regenerá-los.

A variante Nano 2048 int8 usa quantização escalar por dimensão, calibrada nos 600 documentos congelados. A qualidade é calculada após dequantização com as mesmas faixas. O teste registra armazenamento de 2.048 bytes por vetor, mas não declara latência de banco vetorial int8 nativo.

## Rerankers

- baseline sem reranker;
- Qwen local descoberto em `rerank/`, `reranker/`, `models/` ou `embed/`;
- Voyage `rerank-2.5`.

O runner tenta o Qwen mais forte primeiro e registra falhas antes de usar o próximo candidato. Também é possível indicar um caminho explícito com `--qwen-model-path`.

Os dois rerankers recebem:

- a mesma consulta;
- o mesmo texto original das cenas;
- a união estável dos candidatos recuperados;
- a mesma instrução;
- os mesmos candidatos de cada pipeline.

Configuração principal:

- candidatos preservados: top 50;
- reranking: top 20.

## Proteção de API

O Voyage `rerank-2.5` fica desativado por padrão. Ele somente é chamado com:

```bash
--allow-voyage-rerank-api
```

A chave deve permanecer fora do Git, em arquivo local com permissão `0600`. O checkpoint retomável do reranker fica em `results/raw/reranker/` e não deve ser versionado.

## Execução

A partir da raiz do repositório:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python

"$PYTHON" -m pip install -r benchmark/embedding-v3/requirements-reranker.txt

cd benchmark/embedding-v3

PYTHONPATH=. "$PYTHON" reranker_benchmark.py --phase preflight
PYTHONPATH=. "$PYTHON" reranker_benchmark.py --phase candidates
PYTHONPATH=. "$PYTHON" reranker_benchmark.py --phase qwen
PYTHONPATH=. "$PYTHON" reranker_benchmark.py --phase report
```

Após validar o Qwen local, execute a referência Voyage autorizada:

```bash
PYTHONPATH=. "$PYTHON" reranker_benchmark.py \
  --phase voyage \
  --allow-voyage-rerank-api

PYTHONPATH=. "$PYTHON" reranker_benchmark.py --phase report
```

A execução integral também pode ser feita com:

```bash
PYTHONPATH=. "$PYTHON" reranker_benchmark.py \
  --phase all \
  --allow-voyage-rerank-api
```

## Artefatos

Resultados versionáveis:

- `results/reranker/preflight.json`;
- `results/reranker/candidate_summary.json`;
- `results/reranker/candidates/*.json`;
- `results/reranker/scores/*.json`;
- `results/reranker/pipelines/**/*.json`;
- `results/reranker/summary.json`;
- `RERANKER_PIPELINE_REPORT.md`.

Não versionar:

- `results/raw/reranker/`;
- chaves, tokens ou variáveis de ambiente;
- pesos de modelos;
- caches;
- logs brutos;
- ambiente virtual.

## Métricas obrigatórias

Qualidade:

- HitRate e Recall nos cortes existentes;
- MRR@10;
- nDCG@10;
- hard-negative error rate;
- resultado por tipo de consulta.

Efeito do reranker:

- cobertura do conjunto candidato;
- HitRate@1 condicionado à presença do relevante;
- rescue count e rescue rate;
- damage count e damage rate;
- mudança média e mediana da posição relevante.

Operação:

- tempo de carregamento;
- latência p50, p95 e máxima do reranker;
- RAM do processo e subprocessos;
- VRAM;
- CPU;
- tamanho dos pesos;
- dimensão, dtype e bytes por vetor;
- requisições, retries, tokens e tempo de API.

## Regra de decisão

O relatório não escolhe automaticamente uma arquitetura de produção. Ele apresenta separadamente:

- melhor qualidade absoluta;
- melhor pipeline totalmente local;
- melhor uso de armazenamento;
- diferença entre Qwen local e Voyage `rerank-2.5` para os mesmos candidatos.

Merge, integração e implantação dependem de autorização do diretor.
