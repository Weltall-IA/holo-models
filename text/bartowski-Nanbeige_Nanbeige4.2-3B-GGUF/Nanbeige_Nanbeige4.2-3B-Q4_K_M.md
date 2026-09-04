# Nanbeige_Nanbeige4.2-3B-Q4_K_M

## Identificação técnica

- Arquivo GGUF: `Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf`
- Tamanho local registrado: `2,684,354,560` bytes (`2.50 GiB`)
- SHA256: `b92d2e35c9876b0c4bc671996360204f4149d0546c23d5954d5eb3b106c81f24`
- Origem: `bartowski/Nanbeige_Nanbeige4.2-3B-GGUF`
- Arquitetura: Nanbeige 4.2, dense 3B
- Quantização: `Q4_K_M`
- Status no workspace: **modelo leve de código/assistência**

## Especialidade, pontos fortes e trade-offs

- Excelente eficiência de memória para um modelo local auxiliar.
- Resultado de código forte para 3B: 5/6, incluindo 3/3 em C++20.
- Boa opção quando VRAM livre e baixo custo de execução são mais importantes que qualidade máxima.
- Em Python complexo perdeu `PY03`; não substitui o GSQ como coder principal.
- Escrita é funcional, mas fica abaixo dos 27B especializados.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime de referência registrado nos benchmarks: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`; 8 threads; full GPU offload; Flash Attention ON.

Última validação referenciada neste perfil: `2026-09-03`.

### Código — `coding-mini-v1`

Fonte: `benchmarks/coding-mini-v1/` e `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`.

- Score: **5/6**
- Python: **2/3**
- C++20: **3/3**
- Mediana de decode: **18.48 tok/s**
- Pico de VRAM consolidado: **4,519 MiB**
- Falha relevante: `PY03`

### Escrita — `chat-writing-v1` / rodada de candidatos

- Score qualitativo geral: **3.25/5**
- Neutral: **3.38/5**
- Adult: **3.12/5**
- Velocidade registrada: **18.68 tok/s**
- Pico de VRAM registrado no perfil de escrita: **4,519 MiB**
- Observação: tendência leve a inserir títulos/estrutura Markdown em narrativa.

### Speculative decoding

- DFlash2: **N/A / não aplicável ao preset atual**
- MTP: **N/A / não testado**

## DECLARADO PELO AUTOR/ORIGEM

Metadados de arquitetura/origem são mantidos separados dos resultados locais. Nenhum score externo é usado para classificar este modelo no workspace.

## Preset recomendado

```bash
/home/alpha/.local/bin/llama serve \
  -m text/bartowski-Nanbeige_Nanbeige4.2-3B-GGUF/Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q8_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```

Template recomendado: **nativo/embutido**. Não usar Froggeric sem benchmark específico.

## Proveniência

- Código: `benchmarks/coding-mini-v1/`
- Ranking consolidado: `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`
- Escrita: `benchmarks/chat-writing-v1/` e artefatos da rodada de candidatos
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
