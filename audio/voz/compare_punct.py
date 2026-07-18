#!/usr/bin/env python3
import subprocess
import json
import sys

models = [
    "lucasmg09/Qwen3.5-4B-PTBR",
    "lucasmg09/Qwen3.5-0.8B-PTBR", 
    "lucasmg09-Qwen3.5-2B-PTBR",
    "Qwen3-0.6B",
    "marinarosa-MiniCPM5-1B-PTBR-v5-GGUF",
]

frases = [
    ("PEQUENA", "olá tudo bem"),
    ("MÉDIA", "ontem fui ao mercado comprar pão e leite mas esqueci a lista no celular"),
    ("GRANDE", "o presidente da república anunciou ontem uma nova política econômica durante discurso na praça da sétienda frente a uma multidão de aproximadamente três mil pessoas que lotou a região centro da cidade de são paulo onde ele destacou a importância da união das forças política para enfrentar a crise fiscal que atinge o país há meses os índices de inflação sobem e os investidores estrangeiros temem por novas regras impostos pelo governo federal que podem impactar o mercado de capitais"),
]

for model in models:
    print(f"\n=== {model} ===")
    for tipo, frase in frases:
        prompt = f"Ponja esta frase em português. Responda APENAS com a frase pontuada, sem explicações: {frase}"
        try:
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout.strip().split('\n')[-1]
            print(f"[{tipo}] {output[:150]}...")
        except Exception as e:
            print(f"[{tipo}] ERROR: {e}")