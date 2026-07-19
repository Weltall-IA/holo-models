# GATE 2 REPORT

- modo: execução
- resultado: PARTIAL
- corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`

## Modelos

| modelo | backend | revisão | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| voyage4_nano | sentence-transformers | `67fabc9bef01` | 1024 | 0.853333 | 0.752757 | 0.771872 | 30.7029 | 270.2703 |

## Falhas e bloqueios
- `bitnet_270m` (opcional): RuntimeError: llama-server encerrou com código 1
llama-server log tail:
0.00.071.906 I cmn  common_param: common_params_print_info: verbosity = 3 (adjust with the `-lv N` CLI arg)
0.00.071.979 W srv  llama_server: embeddings enabled with n_batch (2048) > n_ubatch (512)
0.00.071.979 W srv  llama_server: setting n_batch = n_ubatch = 512 to avoid assertion failure
0.00.073.727 I srv    load_model: loading model '/home/alpha/Playstoria/models/embed/bitnet_270m/bitnet-embeddings-270m-bf16-i2_s.gguf'
0.00.203.760 E gguf_init_from_reader: tensor 'blk.0.ffn_down.weight' of type 36 (TYPE_IQ4_NL_4_4 REMOVED, use IQ4_NL with runtime repacking) has 2048 elements per row, not a multiple of block size (0)
0.00.203.885 E gguf_init_from_reader: failed to read tensor info
0.00.213.389 E llama_model_load: error loading model: llama_model_loader: failed to load model from /home/alpha/Playstoria/models/embed/bitnet_270m/bitnet-embeddings-270m-bf16-i2_s.gguf
0.00.213.408 E llama_model_load_from_file_impl: failed to load model
0.00.213.471 E common_fit_params: encountered an error while trying to fit params to free device memory: failed to load model
0.00.273.100 E gguf_init_from_reader: tensor 'blk.0.ffn_down.weight' of type 36 (TYPE_IQ4_NL_4_4 REMOVED, use IQ4_NL with runtime repacking) has 2048 elements per row, not a multiple of block size (0)
0.00.273.120 E gguf_init_from_reader: failed to read tensor info
0.00.280.875 E llama_model_load: error loading model: llama_model_loader: failed to load model from /home/alpha/Playstoria/models/embed/bitnet_270m/bitnet-embeddings-270m-bf16-i2_s.gguf
0.00.280.887 E llama_model_load_from_file_impl: failed to load model
0.00.280.903 E cmn  common_init_: failed to load model '/home/alpha/Playstoria/models/embed/bitnet_270m/bitnet-embeddings-270m-bf16-i2_s.gguf'
0.00.280.914 E srv    load_model: failed to load model, '/home/alpha/Playstoria/models/embed/bitnet_270m/bitnet-embeddings-270m-bf16-i2_s.gguf'
0.00.280.920 I srv    operator(): operator(): cleaning up before exit...
0.00.282.571 E srv  llama_server: exiting due to model loading error

- `bitnet_06b` (opcional): RuntimeError: llama-server encerrou com código 1
llama-server log tail:
0.00.068.113 I cmn  common_param: common_params_print_info: verbosity = 3 (adjust with the `-lv N` CLI arg)
0.00.068.286 W srv  llama_server: embeddings enabled with n_batch (2048) > n_ubatch (512)
0.00.068.289 W srv  llama_server: setting n_batch = n_ubatch = 512 to avoid assertion failure
0.00.070.206 I srv    load_model: loading model '/home/alpha/Playstoria/models/embed/bitnet_06b/bitnet-embeddings-0.6b-bf16-i2_s.gguf'
0.00.130.597 E gguf_init_from_reader: tensor 'blk.0.ffn_down.weight' of type 36 (TYPE_IQ4_NL_4_4 REMOVED, use IQ4_NL with runtime repacking) has 3072 elements per row, not a multiple of block size (0)
0.00.130.614 E gguf_init_from_reader: failed to read tensor info
0.00.132.424 E llama_model_load: error loading model: llama_model_loader: failed to load model from /home/alpha/Playstoria/models/embed/bitnet_06b/bitnet-embeddings-0.6b-bf16-i2_s.gguf
0.00.132.430 E llama_model_load_from_file_impl: failed to load model
0.00.132.462 E common_fit_params: encountered an error while trying to fit params to free device memory: failed to load model
0.00.158.162 E gguf_init_from_reader: tensor 'blk.0.ffn_down.weight' of type 36 (TYPE_IQ4_NL_4_4 REMOVED, use IQ4_NL with runtime repacking) has 3072 elements per row, not a multiple of block size (0)
0.00.158.165 E gguf_init_from_reader: failed to read tensor info
0.00.160.279 E llama_model_load: error loading model: llama_model_loader: failed to load model from /home/alpha/Playstoria/models/embed/bitnet_06b/bitnet-embeddings-0.6b-bf16-i2_s.gguf
0.00.160.282 E llama_model_load_from_file_impl: failed to load model
0.00.160.289 E cmn  common_init_: failed to load model '/home/alpha/Playstoria/models/embed/bitnet_06b/bitnet-embeddings-0.6b-bf16-i2_s.gguf'
0.00.160.293 E srv    load_model: failed to load model, '/home/alpha/Playstoria/models/embed/bitnet_06b/bitnet-embeddings-0.6b-bf16-i2_s.gguf'
0.00.160.296 I srv    operator(): operator(): cleaning up before exit...
0.00.160.977 E srv  llama_server: exiting due to model loading error


Cada modelo foi executado em processo isolado. Uma falha CUDA não contamina os modelos seguintes.
Nenhuma API paga foi chamada. Pesos e caches permanecem fora do Git.
