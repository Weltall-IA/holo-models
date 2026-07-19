# GATE 2 REPORT

- modo: execução
- resultado: BLOCKED
- corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`

## Modelos

| modelo | revisão | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |
|---|---|---:|---:|---:|---:|---:|---:|
| nenhum | - | - | - | - | - | - | - |

## Falhas
- `embeddinggemma`: GatedRepoSkipped: modelo gated (manual) sem credenciais de acesso válidas para google/embeddinggemma-300m
- `gte_multilingual_base`: AcceleratorError: CUDA error: unspecified launch failure
Search for `cudaErrorLaunchFailure' in https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__TYPES.html for more information.
CUDA kernel errors might be asynchronously reported at some other API call, so the stacktrace below might be incorrect.
For debugging consider passing CUDA_LAUNCH_BLOCKING=1

- `qwen3_embedding_06`: AcceleratorError: CUDA error: unspecified launch failure
Search for `cudaErrorLaunchFailure' in https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__TYPES.html for more information.
CUDA kernel errors might be asynchronously reported at some other API call, so the stacktrace below might be incorrect.
For debugging consider passing CUDA_LAUNCH_BLOCKING=1

- `bge_m3_dense`: AcceleratorError: CUDA error: unspecified launch failure
Search for `cudaErrorLaunchFailure' in https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__TYPES.html for more information.
CUDA kernel errors might be asynchronously reported at some other API call, so the stacktrace below might be incorrect.
For debugging consider passing CUDA_LAUNCH_BLOCKING=1

- `voyage4_nano`: AttributeError: 'NoneType' object has no attribute '__name__'

Nenhuma API paga foi chamada. Pesos e caches permanecem fora do Git.
