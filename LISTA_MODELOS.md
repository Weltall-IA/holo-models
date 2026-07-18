# Lista de Modelos

Modelos disponíveis e registrados no Ollama (atualizado: 2026-07-10).

## Registrados no Ollama (GPU)
| Modelo | Tipo | Uso típico | Reflink |
|---|---|---|---|
| `lucasmg09/Qwen3.5-2B-PTBR` | LLM GGUF Q4_K_M | Chat / restauração de pontuação | ✅ |
| `lucasmg09/Qwen3.5-4B-PTBR` | LLM GGUF Q6_K | Chat / restauração de pontuação | ✅ |
| `lucasmg09/Qwen3.5-0.8B-PTBR` | LLM GGUF Q6_K | Chat / restauração de pontuação | ✅ |
| `Qwen/Qwen3-0.6B` | LLM GGUF Q8_0 | Chat / restauração de pontuação | ✅ |
| `marinarosa/MiniCPM5-1B-PTBR-v5-GGUF` | LLM GGUF Q4_K_M | Chat / restauração de pontuação | ✅ |
| `Qwen/Qwen3.6-14B-A3B-VibeForged-v2` | LLM GGUF Q4_K_M | Chat / vibecoding | ✅ |

## Não registrados (uso direto via transformers)
| Modelo | Arquitetura | Pipeline |
|---|---|---|
| `dominguessm/bert-restore-punctuation-ptbr` | BERT | punctuation restoration |
| `Polygl0t/Tucano2-qwen-1.5B-Instruct` | Qwen | (safetensors - não-GGUF) |
| `Polygl0t/Tucano2-qwen-3.7B-Instruct` | Qwen | (safetensors - não-GGUF) |

## ASR (transcrição)
| Modelo | Tipo |
|---|---|
| `openai/whisper-large-v3-turbo` | Whisper GGUF (q5_0) |