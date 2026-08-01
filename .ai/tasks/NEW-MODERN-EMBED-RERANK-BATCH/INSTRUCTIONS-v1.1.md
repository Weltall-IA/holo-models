# INSTRUCTIONS v1.1 — correção obrigatória de quantização e telemetria

## Substituição imediata

Esta versão substitui integralmente `INSTRUCTIONS-v1.0.md`.

Se a execução baseada na v1.0 já começou, interrompa imediatamente qualquer download, conversão ou carregamento de pesos locais nativos FP32, FP16 ou BF16. Não apague automaticamente arquivos já baixados; registre caminho, tamanho e estado parcial para decisão posterior. Continue somente após atualizar para esta versão e resolver os artefatos quantizados exatos.

## Fonte canônica da política de quantização

Leia e aplique obrigatoriamente:

`benchmark/embedding-v3/config/CANONICAL_BENCHMARK_CANDIDATES.json`

A seção `quantization_policy` desse arquivo é vinculante para todos os embeddings e rerankers locais.

Ordem obrigatória:

1. `NVFP4` compatível e comprovado;
2. `Q4_K_M` compatível e comprovado;
3. outra variante `Q4` somente quando NVFP4 e Q4_K_M não existirem ou forem incompatíveis.

A mesma ordem também aparece em `artifact_priority` de cada candidato local.

## Proibições

É proibido:

- baixar pesos nativos FP32, FP16 ou BF16;
- baixar Q8 para modelos maiores que 1B;
- usar o repositório oficial genérico como autorização implícita para baixar shards nativos;
- iniciar download antes de resolver o artefato exato;
- converter silenciosamente um peso nativo já baixado;
- substituir um candidato quantizado por outro modelo ou revisão;
- tratar ausência de quantização como autorização para usar precisão nativa.

A única exceção possível é para modelo local de até 1B quando não existir artefato NVFP4 ou Q4 compatível. Essa exceção exige, cumulativamente:

- busca documentada por NVFP4 e Q4;
- prova de inexistência ou incompatibilidade;
- preflight de memória;
- autorização explícita do usuário antes do download nativo.

Sem essa autorização, registrar `BLOCKED_QUANTIZED_ARTIFACT_UNAVAILABLE` e manter o candidato na fila.

## Resolução obrigatória antes de qualquer download

Para cada peso local, registrar antes do download:

- família do modelo;
- repositório exato;
- revisão ou commit;
- nome exato do arquivo;
- formato;
- quantização;
- tamanho em bytes;
- licença;
- runtime compatível;
- URL ou origem;
- motivo de escolha conforme a prioridade NVFP4 → Q4_K_M → Q4.

Nenhum download pode começar enquanto algum desses campos estiver ausente.

## Telemetria obrigatória

Toda execução local de embedding, reranker e pipeline combinado deve registrar telemetria completa. Não usar `quando disponível` como desculpa; implementar coleta quando o runtime não fornecer diretamente.

Registrar no mínimo:

### Identidade e ambiente

- modelo, revisão, arquivo, quantização, tamanho e SHA-256;
- backend e versão;
- versão do CUDA, driver e runtime;
- CPU exata;
- GPU exata;
- RAM total;
- VRAM total;
- número de threads;
- parâmetros de execução.

### Memória

- RAM baseline antes do carregamento;
- RAM após carregamento;
- RAM pico durante a execução;
- delta de RAM;
- VRAM baseline antes do carregamento;
- VRAM após carregamento;
- VRAM pico durante a execução;
- delta de VRAM;
- memória combinada do pipeline com embedding e reranker residentes simultaneamente;
- OOM, swap e page faults relevantes.

### CPU e GPU

- utilização média e pico de CPU;
- utilização média e pico de GPU;
- temperatura média e máxima da GPU;
- potência média e máxima da GPU quando exposta por `nvidia-smi`;
- clocks relevantes quando disponíveis;
- utilização de memória da GPU ao longo da execução;
- amostragem periódica, com intervalo registrado.

### Tempos e desempenho

- tempo de download, quando houver;
- tempo de carregamento;
- tempo de warmup;
- duração total;
- throughput;
- latências p50, p95, p99 e máxima;
- número de entradas processadas;
- erros, retries, timeouts e falhas.

### Raw embedding

- tempo para indexar os 600 documentos;
- documentos por segundo;
- tempo para processar as 150 consultas;
- consultas por segundo;
- dimensão e dtype de saída;
- candidates top 50 persistidos;
- métricas raw completas.

### Reranker

- tempo de carregamento isolado;
- pares processados;
- pares por segundo;
- latência por consulta;
- tamanho do lote;
- top 50 de entrada e top 20 reranqueado;
- métricas completas.

### Pipeline combinado

- embedding e reranker carregados simultaneamente;
- RAM e VRAM combinadas;
- latência fim a fim por consulta;
- throughput fim a fim;
- erros e estabilidade;
- confirmação de que não houve descarregamento silencioso entre etapas.

Para APIs remotas, registrar `RAM/VRAM local = NOT_APPLICABLE_REMOTE_API`, além de:

- tokens;
- requisições;
- duração;
- latências p50, p95, p99 e máxima;
- throughput;
- cota utilizada;
- retries e erros;
- confirmação de ausência de cobrança.

## Artefatos e consolidação

Criar artefato individual autoritativo para cada raw e cada pipeline reranqueado.

Atualizar obrigatoriamente:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

O consolidado deve conter a política de quantização aplicada, o artefato exato escolhido e toda a telemetria acima.

Não criar leaderboard, registry, fila, matriz ou resumo paralelo.

## Continuidade da tarefa

Após aplicar esta correção, retome a execução da v1.0 apenas nos pontos ainda válidos:

- mesmos candidatos da fila canônica;
- raw primeiro;
- todos os rerankers locais ou gratuitos elegíveis;
- mesmo corpus congelado;
- atualização do consolidado único;
- nenhum merge.

## Retorno obrigatório

Além do retorno já exigido pela v1.0, informar:

1. downloads interrompidos pela política nova;
2. arquivos nativos já baixados, sem apagá-los automaticamente;
3. artefato quantizado escolhido para cada modelo;
4. justificativa de qualquer bloqueio por ausência de NVFP4/Q4;
5. tabela completa de RAM, VRAM, CPU, GPU, temperaturas, potência, tempos, throughput e latências;
6. confirmação de que nenhum peso local FP32, FP16 ou BF16 foi usado sem autorização explícita.

Frase final obrigatória:

`Política NVFP4 → Q4_K_M → Q4 aplicada antes de qualquer download, com telemetria completa de RAM, VRAM, CPU, GPU e desempenho registrada em todos os benchmarks.`