# Runbook de Reprodução — Qwen3.8-27B 16GB Quick Benchmark v1

Este documento descreve os passos exatos para reproduzir 100% deste benchmark local de forma determinística e isolada.

## 1. Requisitos de Ambiente
- GPU NVIDIA RTX 5060 Ti 16 GB (ou compatível com 16 GB VRAM)
- Driver NVIDIA >= 610.x, CUDA UMD 13.x
- Linux x86_64
- Python 3.11+ com `huggingface_hub`, `pytest`, `requests`
- `llama-server` compilado com suporte CUDA e Flash Attention

## 2. Estrutura Canônica de Modelos
Os modelos devem ser baixados estritamente na pasta canônica `text/<origem-quantizacao>/`:
- `text/armand0e-Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M/`
- `text/mradermacher-Qwen3.8-27B-Uncensored-Heretic-T10-BF16-i1-IQ3_M/`
- `text/Bucoid-Qwen3.8-27B-Heretic-Ara-IQ4_XS/`
- `text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/`
- `text/mradermacher-Ektome-Qwen3.8-27B-PristinelyUncensored-i1-IQ3_M/`
- `text/0bserverx-Qwen3.8-27B-Heretic-Abliterated-Uncensored-Q3_K_M/`

## 3. Comandos de Execução
```bash
# 1. Download e validação SHA256
python3 tasks/qwen38-27b-16gb-quick-v1/download_models.py

# 2. Execução completa automatizada (Fase 1 + Seleção Top 3 + Fase 2 32K/64K)
python3 tasks/qwen38-27b-16gb-quick-v1/run_benchmark.py
```
