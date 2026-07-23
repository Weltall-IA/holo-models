# Relatório Nemotron 1.0.5

Estado: `COMPLETED`

## Escopo executado

Esta execução corrigiu a licença, inspecionou os dois GGUFs Nemotron 8B, repetiu
as inicializações, concluiu o preflight NVFP4 em ambiente isolado e comparou os
perfis Nemotron 1B NVFP4 e GGUF no corpus completo. Pesos, caches e o ambiente
virtual permaneceram fora do Git.

O smoke test de três textos foi usado somente como preflight. A decisão de
admissão usa o corpus congelado completo, com 600 documentos, 150 consultas e
SHA-256 conjunto
`8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`.

## Licença

A licença dos pesos Nemotron é `OpenMDW-1.1`.

- `nvidia/Nemotron-3-Embed-1B-NVFP4`: o arquivo local `LICENSE` declara que os
  modelos binários e os arquivos-fonte são licenciados sob OpenMDW-1.1; o model
  card repete a mesma declaração.
- `Abiray/Nemotron-3-Embed-8B-GGUF`: o GGUF embute
  `general.license.name=openmdw-1.1` e
  `general.license.link=https://openmdw.ai/license/1-1/`.
- `Aqua00/Nemotron-3-Embed-8B-GGUF`: contém as mesmas declarações embutidas.
- `zenmagnets/Nemotron-3-Embed-1B-Q4_K_M-GGUF`: a publicação do conversor
  declara OpenMDW-1.1; nome, tamanho e SHA-256 publicados coincidem com o
  arquivo local.

A licença Apache 2.0 do Ministral subjacente não foi usada como licença dos
pesos Nemotron.

## Identidade dos pesos

| perfil | bytes | SHA-256 |
|---|---:|---|
| Nemotron 8B Abiray Q4_K_M | 4.896.390.039 | `a2aa29c618da6eed10d9474e72e33188c61e5fd700aed2fe9a1d98abdc90c6fc` |
| Nemotron 8B Aqua00 Q4_K_M | 4.896.389.984 | `1352d929879c61fccf76ff855c6250c7fdc924479932918febcc6fe384cb70a7` |
| Nemotron 1B NVFP4 `model.safetensors` | 1.027.789.672 | `f2753954c89055eb679a45b7dfea27a3e05c04ecbdb1f4e6c086180fe8c32bc7` |
| Nemotron 1B GGUF Q4_K_M | 749.352.096 | `9a74166f51dbc280073748fa199bea49283bd21f7f9280f2dec2b4d975ddfd1d` |

## Inspeção dos GGUFs 8B

Os dois arquivos são GGUF v3, little-endian, com 51 pares de metadados e 308
tensores. O início da área de dados é o offset `7.879.520`; o último tensor
termina no offset `4.896.389.984`.

O diff estrutural produziu:

- mesmas 51 chaves e mesmos valores de metadados;
- SHA-256 idêntico de todo o cabeçalho serializado:
  `afdf5360cfade68e5145973eb6c637fa34f63726d3db9e1979070ecb314d888f`;
- mesmos 308 nomes, formas e tipos de tensor;
- 308 de 308 SHA-256 dos payloads brutos de tensor idênticos;
- nenhuma diferença de hash por tensor.

Os arquivos completos não são bit a bit idênticos. O Aqua00 termina exatamente
ao fim do último tensor. O Abiray tem mais 55 bytes depois do conteúdo GGUF
estruturado:

```text
\nL2P_bypass_Nemotron-3-Embed-8B-Q4_K_M.gguf_1784618362\n
```

Classificação: conteúdo GGUF válido e payloads de tensor equivalentes; arquivos
completos distintos por uma anotação extra não estrutural no Abiray. Essa
classificação decorre da inspeção binária, estrutural e por tensor, e não do
pequeno corpus de embeddings.

Evidência consolidada:
`results/nemotron_audit_1_0_5/gguf_8b_comparison.json`.

## Cinco inicializações alternadas por GGUF 8B

A ordem executada foi:
`Abiray, Aqua00, Abiray, Aqua00, Abiray, Aqua00, Abiray, Aqua00, Abiray, Aqua00`.
Todas as dez inicializações foram `EXECUTED`, em CUDA, com `llama-server`
9972 (`c92e806d1`), pooling mean, offload integral e duas entradas por execução.

| conversor | execuções | startup médio (s) | faixa startup (s) | embeddings/s médio | RSS pico médio (MiB) | VRAM pico (MiB) |
|---|---:|---:|---:|---:|---:|---:|
| Abiray | 5 | 5,001516 | 3,118513–9,750628 | 11,647697 | 5.081,188 | 5.218 |
| Aqua00 | 5 | 3,815711 | 2,849149–7,019506 | 12,077820 | 5.081,328 | 5.218 |

As cinco execuções de cada arquivo retornaram duas embeddings de 4.096
dimensões. Os logs individuais estão em
`results/nemotron_audit_1_0_5/gguf_startup_logs/`.

## Preflight isolado do NVFP4

O NVFP4 foi executado exclusivamente com vLLM no ambiente isolado
`/tmp/vllm-env`. Não foram usados Transformers, Sentence Transformers,
llama.cpp nem Ollama para carregar ou inferir o NVFP4.

Ambiente:

- Python 3.12.13;
- vLLM 0.25.0;
- PyTorch 2.11.0+cu130;
- CUDA do PyTorch 13.0;
- NVIDIA GeForce RTX 5060 Ti, 16.311 MiB;
- driver NVIDIA 610.43.03;
- arquitetura reconhecida: `Ministral3Model`;
- quantização reconhecida: `modelopt_fp4`;
- runner: pooling, mean, embeddings de 2.048 dimensões.

A primeira inicialização válida foi limitada a `MAX_JOBS=1` para impedir nova
pressão excessiva sobre a RAM durante a compilação CUDA. Ela compilou 16 objetos
CUDA e avaliou 40 configurações de autotune.

| condição NVFP4 | carga (s) | inferência de 3 textos (s) | embeddings/s | RSS pico (MiB) | VRAM pico (MiB) |
|---|---:|---:|---:|---:|---:|
| primeira compilação | 1.568,952814 | 30,190240 | 0,099370 | 7.052,852 | 2.056 |
| cache aquecido | 18,718944 | 0,093718 | 32,011013 | 3.492,234 | 2.052 |

O custo excepcional ocorre na construção inicial dos kernels e não representa
o regime permanente. O cache compilado foi preservado fora do Git. Os logs e
amostras de memória estão em
`results/nemotron_audit_1_0_5/nvfp4_attempt_20260723_serial/` e
`results/nemotron_audit_1_0_5/nvfp4_cached_20260723/`.

## Preflight comparativo Nemotron 1B

No smoke test de três textos, os dois perfis colocaram a passagem relevante
acima da irrelevante. A margem foi 0,333633 no NVFP4 e 0,298167 no GGUF. Isso
não foi usado como conclusão de qualidade geral.

| perfil | startup/carga (s) | inferência (s) | embeddings/s | RSS pico (MiB) | VRAM pico (MiB) |
|---|---:|---:|---:|---:|---:|
| NVFP4 cache aquecido | 17,140081 | 0,115742 | 25,919654 | 3.107,113 | 2.056 |
| GGUF Q4_K_M | 3,289369 | 0,141849 | 21,149319 | 1.113,180 | 1.218 |

A similaridade de cada texto entre backends ficou entre 0,969169 e 0,976065.
Os formatos não são aliases e permanecem perfis distintos.

## Benchmark completo de admissão Nemotron 1B

Protocolo comum: 600 documentos, 150 consultas, prefixos oficiais `passage: `
e `query: `, pooling mean, normalização L2 e contexto 1.024.

| métrica | NVFP4 | GGUF Q4_K_M |
|---|---:|---:|
| HitRate@1 | 0,740000 | 0,726667 |
| HitRate@10 | 0,846667 | 0,853333 |
| MRR@10 | 0,775341 | 0,769508 |
| nDCG@10 | 0,784982 | 0,782019 |
| erro de negativo difícil | 0,133333 | 0,133333 |

Bootstrap pareado com 20.000 reamostragens, sempre NVFP4 menos GGUF:

| métrica | delta | intervalo de 95% |
|---|---:|---:|
| HitRate@1 | +0,013333 | [-0,013333; 0,040000] |
| HitRate@10 | -0,006667 | [-0,033333; 0,013333] |
| MRR@10 | +0,005833 | [-0,007889; 0,021056] |
| nDCG@10 | +0,002963 | [-0,009419; 0,015748] |

Todos os intervalos incluem zero. Não foi estabelecida superioridade de
qualidade entre os perfis nesse corpus. Em primeiro rank relevante, o NVFP4 foi
melhor em 20 consultas, o GGUF em 14 e houve 116 empates; a sobreposição média
do top 10 foi 0,872667.

Regime aquecido:

| perfil | carga (s) | docs/s | consultas/s | total (s) | RSS pico (MiB) | VRAM pico (MiB) |
|---|---:|---:|---:|---:|---:|---:|
| NVFP4 | 16,246897 | 145,025645 | 414,135936 | 28,392365 | 3.573,387 | 2.072 |
| GGUF Q4_K_M | 1,324476 | 17,689908 | 98,240613 | 37,269758 | 1.213,484 | 1.288 |

O NVFP4 teve aproximadamente 8,20 vezes o throughput de documentos e 4,22
vezes o throughput de consultas. O GGUF teve carga fria muito menor e consumiu
aproximadamente 2.360 MiB menos RAM e 784 MiB menos VRAM no pico medido.

A repetição NVFP4 preservou exatamente os rankings top 50, mas não os hashes
bit a bit das embeddings float. A reprodutibilidade observada é de ranking, não
determinismo binário das embeddings.

Decisão: os dois perfis estão `APPROVED` para o benchmark completo e devem ser
reportados separadamente. NVFP4 é o padrão operacional para lotes em NVIDIA;
GGUF é a opção de menor consumo e menor cold start.

## Branch

A execução começou em `ai/reranker-benchmark-v1.5` porque o handoff interrompido,
os downloads e os artefatos não versionados já estavam nesse worktree. Eles
foram preservados no lugar para não sobrescrever, mover ou esconder trabalho
preexistente. O trabalho da correção 1.0.5 deve ser publicado em uma feature
branch dedicada antes do commit, mantendo no relatório a origem operacional.

## Arquivos e evidências

- fila persistente: `.ai/tasks/NEMOTRON-AUDIT-1.0.5/STATUS.yml`;
- perfis admitidos: `config/nemotron_1b_profiles.json`;
- comparação estrutural: `results/nemotron_audit_1_0_5/gguf_8b_comparison.json`;
- hashes completos dos arquivos: `results/nemotron_audit_1_0_5/file_sha256.txt`;
- hashes por tensor: `results/nemotron_audit_1_0_5/{abiray,aqua00}_tensor_hashes.txt`;
- dez inicializações: `results/nemotron_audit_1_0_5/gguf_startups.json`;
- decisão de admissão: `results/nemotron_audit_1_0_5/admission_decision_20260723.json`;
- manifesto completo: `results/nemotron_audit_1_0_5/manifest.json`;
- diff completo do escopo: `results/nemotron_audit_1_0_5/full_diff.patch`.

Os scripts de execução e consolidação estão na raiz de
`benchmark/embedding-v3/`. O manifesto registra tamanho e SHA-256 de cada
arquivo versionado nesta correção.

## Limites da conclusão

- A igualdade dos tensores 8B não torna os arquivos completos idênticos.
- O benchmark mede o corpus Holo congelado e não prova superioridade universal.
- Tempos e memória são específicos deste host, destas versões e configurações.
- A primeira compilação NVFP4 é um custo de preparação; caches podem ser
  invalidados por mudanças de GPU, driver, CUDA, vLLM ou perfil de execução.
