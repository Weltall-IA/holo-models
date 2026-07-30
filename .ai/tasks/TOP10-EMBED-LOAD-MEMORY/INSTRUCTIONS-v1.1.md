# INSTRUCTIONS v1.1 — memória de carregamento dos embeddings líderes sem perfil 4096

## Substituição

Esta instrução substitui integralmente `INSTRUCTIONS-v1.0.md` para a rodada `TOP10-EMBED-LOAD-MEMORY`.

## Objetivo

Medir, de forma curta e isolada, o custo de carregamento dos embeddings que representam o top 10 operacional atual do benchmark Holo, excluindo explicitamente o perfil Nemotron 8B em 4096 dimensões.

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

## Top 10 operacional desta rodada

Use o ranking publicado por MRR@10, mas aplique a decisão operacional explícita abaixo:

- excluir `nemotron_8b_abiray_q4_audit_4096` da shortlist;
- promover a antiga posição 11, `nomic_embed_text_v2_moe_q4__qwen_local`, para a posição operacional 10;
- não carregar, medir, publicar nem recomendar o perfil 4096 nesta rodada;
- manter `nemotron_8b_abiray_q4_audit_1024` como única variante operacional do Nemotron 8B.

A lista de posições operacionais esperada é:

1. `qwen3_embedding_4b_q8_0__llama_nemotron_rerank_1b_v2`;
2. `nomic_embed_text_v2_moe_q4__llama_nemotron_rerank_1b_v2`;
3. `nemotron_3_embed_1b_nvfp4__llama_nemotron_rerank_1b_v2`;
4. `nemotron_8b_abiray_q4_audit_1024__voyage_rerank_2_5`;
5. `colibri_ptbr__llama_nemotron_rerank_1b_v2`;
6. `embeddinggemma__llama_nemotron_rerank_1b_v2`;
7. `embeddinggemma_768_float32__voyage_rerank_2_5`;
8. `voyage_4_large_1024_float32__voyage_rerank_2_5`;
9. `qwen3_embedding_4b_q8_0__qwen_local`;
10. `nomic_embed_text_v2_moe_q4__qwen_local`.

O 11º promovido usa o mesmo embedding Nomic da posição 2. Portanto, a promoção altera o top 10 operacional, mas não cria um novo peso local a carregar.

## Escopo dos pesos

Deduplique as posições por peso local real.

O conjunto esperado inclui:

1. `qwen3_embedding_4b_q8_0`;
2. `nomic_embed_text_v2_moe_q4`;
3. `nemotron_3_embed_1b_nvfp4`;
4. `nemotron_8b_abiray_q4_audit_1024`;
5. `colibri_ptbr`;
6. `embeddinggemma` e `embeddinggemma_768_float32`, medidos uma única vez somente quando a identidade do peso for comprovadamente a mesma;
7. `voyage_4_large_1024_float32`, registrado como remoto/API e não carregado localmente.

Regras:

- `nemotron_8b_abiray_q4_audit_4096` está fora do escopo, mesmo compartilhando o GGUF com 1024.
- Não carregue o mesmo arquivo de peso duas vezes apenas porque há dois pipelines ou rerankers diferentes.
- Para modelos Voyage/API, não tente baixar ou reconstruir pesos proprietários. Registre `REMOTE_API_NO_LOCAL_LOAD`, parâmetros/tamanho local como não publicados ou não aplicáveis e consumo local de modelo como `0`, distinguindo isso do cliente HTTP.
- Não substitua um artefato por outro parecido.
- Não baixe pesos novos sem necessidade. Use somente pesos já existentes e verificados no host.
- Se um peso local esperado não estiver disponível, registre `BLOCKED_MISSING_LOCAL_WEIGHT` com caminho esperado e evidência da busca.

## Nota sobre 1024 versus 4096

As variantes 1024 e 4096 usam o mesmo peso GGUF e, portanto, têm praticamente o mesmo custo de carregamento do modelo. A exclusão de 4096 é uma decisão de armazenamento vetorial e operação:

- FP32: 4096 dimensões usam 4 vezes o espaço de 1024;
- FP16: 4096 dimensões também usam 4 vezes o espaço de 1024;
- para 600 documentos, somente os vetores FP32 ocupam aproximadamente 9,38 MiB em 4096 contra 2,34 MiB em 1024, antes de índice e metadados;
- em coleções grandes, essa razão de 4 vezes permanece.

Não apresente a exclusão de 4096 como economia de tamanho do peso ou de VRAM de carregamento.

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
6. executar apenas um smoke mínimo de uma consulta curta e um documento curto;
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
- quantização/dtype;
- parâmetros declarados no nome ou metadados oficiais, sem removê-los do nome humano, por exemplo `EmbeddingGemma 300M`.

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
- lista das 10 posições operacionais desta instrução;
- registro explícito da exclusão do perfil 4096;
- mapa de deduplicação entre pipelines, IDs e pesos reais;
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

Se um runtime reportar memória reservada que não pode ser atribuída com precisão, registre separadamente `allocated`, `reserved` e consumo observado pelo driver.

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

`Measure isolated load memory for operational top embeddings`

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
2. lista das 10 posições operacionais;
3. confirmação da exclusão de `nemotron_8b_abiray_q4_audit_4096`;
4. pesos locais únicos realmente medidos;
5. mapa de IDs/pipelines duplicados para o mesmo peso;
6. tabela completa com parâmetros, MB, MiB, RAM idle/pico, VRAM idle/pico e load time;
7. modelos API/remotos e por que não possuem carga local;
8. bloqueios;
9. testes e validações;
10. arquivos alterados;
11. commit, push e PR;
12. confirmação de que nenhum reranker e nenhuma API paga foram usados.

Frase final:

`v1.1 — memória isolada dos embeddings líderes medida sem reranker e sem perfil Nemotron 4096.`
