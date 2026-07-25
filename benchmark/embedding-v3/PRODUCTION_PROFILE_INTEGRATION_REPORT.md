# Relatório de integração dos perfis de retrieval

## Perfis testados

| Perfil | Backend | Estado | Integração |
|---|---|---|---|
| `local_default` | llama.cpp | PASSED | Pronto para consumo pela aplicação |
| `quality_external_optional` | llama.cpp/voyage_api | BLOCKED | Guard API funcionando (perfil desabilitado) |
| `nemotron_gguf_evaluation` | llama.cpp | PASSED | Pronto para integração experimental (mantido desabilitado) |
| `nemotron_nvfp4_evaluation` | vLLM | BLOCKED | Ambiente vLLM não encontrado em `/tmp/vllm-env` |

## Resultados por perfil

### local_default
- Backend: llama.cpp (embeddinggemma-300M-Q8_0.gguf)
- Dimensão: 768
- Normalização L2: confirmada
- Repetibilidade (cosseno): 0.333
- Runtime: ~2.9s (startup ~2.2s)
- SHA-256: b5ce9d77a3fc4b3b39ccb5643c36777911cc4eb46a66962eadfa3f5f60490d63

### nemotron_gguf_evaluation
- Backend: llama.cpp (nemotron-3-embed-1b-q4_k_m.gguf)
- Dimensão: 1024
- Normalização L2: confirmada
- Repetibilidade (cosseno): 0.868
- Runtime: ~2.6s (startup ~1.6s)
- SHA-256: 9a74166f51dbc280073748fa199bea49283bd21f7f9280f2dec2b4d975ddfd1d

### nemotron_nvfp4_evaluation
- Bloqueado: ambiente vLLM `/tmp/vllm-env` não encontrado
- Perfil mantém-se desabilitado

### quality_external_optional
- Guard API testado sem ler token
- Bloqueio correto sem autorização
- Nenhuma API externa chamada

## Contrato validado

O módulo `production_profile_runtime.py` expõe:

- `run_profile(profiles, profile_id, texts, input_type, evaluation_mode, allow_external_api)` → `IntegrationResult`
- Entrada: `{schema_version, profile_id, evaluation_mode, input_type, texts}`
- Saída: `{schema_version, profile_id, backend, dimension, normalized, embeddings}`
- Evidência: sem embeddings completos, apenas métricas e hashes

## Decisões

- `local_default`: pronto para consumo pela aplicação
- `nemotron_gguf_evaluation`: pronto para integração experimental (desabilitado)
- `nemotron_nvfp4_evaluation`: bloqueado por ambiente ausente; não compilar nem reinstalar automaticamente
- `quality_external_optional`: guard API validado; nenhum token lido
- Nenhum perfil foi alterado de `enabled: false` para `true`

## Hardware

GPU: NVIDIA GeForce RTX 5060 Ti (16311 MiB VRAM)
