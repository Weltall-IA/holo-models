#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API = "http://127.0.0.1:11434/api"
ROOT = Path(
    "/home/alpha/Playstoria/models/benchmarks/"
    "local-chat-v1/round-01-ollama-calibration"
)
START_LOCAL = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
OUT = ROOT / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

MODELS = [
    "Qwen/Qwen3-0.6B-Q8_0",
    "lucasmg09/Qwen3.5-0.8B-PTBR-Q6_K",
    "marinarosa/MiniCPM5-1B-PTBR-v5-Q4_K_M",
    "lucasmg09/Qwen3.5-2B-PTBR-Q4_K_M",
    "qwythos-9b-v2-mtp",
]

OPTS = {
    "temperature": 0,
    "seed": 42,
    "num_ctx": 4096,
    "num_predict": 512,
}

CASES = [
    (
        "00_cold_probe",
        "cold_load",
        [
            {
                "role": "system",
                "content": (
                    "Responda em portugu\xeas brasileiro e siga literalmente "
                    "a instru\xe7\xe3o."
                ),
            },
            {
                "role": "user",
                "content": "Responda apenas: PRONTO",
            },
        ],
        None,
        None,
    ),
    (
        "01_ptbr_natural",
        "portuguese",
        [
            {
                "role": "user",
                "content": (
                    "Uma cliente escreveu: 'Oi, mandei as fotos ontem e queria "
                    "saber se j\xe1 ficaram prontas'. Responda como atendente de "
                    "uma gr\xe1fica brasileira, com exatamente duas frases, tom "
                    "cordial, sem prometer prazo que n\xe3o foi informado."
                ),
            }
        ],
        None,
        None,
    ),
    (
        "02_reasoning",
        "reasoning",
        [
            {
                "role": "user",
                "content": (
                    "Em uma fila, Ana est\xe1 antes de Bruno. Caio est\xe1 depois de "
                    "Bruno. Davi est\xe1 antes de Ana. Informe a ordem \xfanica das "
                    "quatro pessoas e explique em uma frase."
                ),
            }
        ],
        None,
        None,
    ),
    (
        "03_instruction",
        "instruction_following",
        [
            {
                "role": "user",
                "content": (
                    "Escreva exatamente tr\xeas linhas, sem marcadores e sem "
                    "texto adicional.\n"
                    "Linha 1: OLLAMA\n"
                    "Linha 2: VANE\n"
                    "Linha 3: SEARXNG"
                ),
            }
        ],
        None,
        None,
    ),
    (
        "04_structured_json",
        "json",
        [
            {
                "role": "user",
                "content": (
                    "O Vane responde HTTP 200, mas a pesquisa retorna zero "
                    "resultados. Produza o JSON solicitado com diagn\xf3stico "
                    "prudente, duas a\xe7\xf5es de verifica\xe7\xe3o e risco 'baixo', sem "
                    "afirmar causa n\xe3o comprovada."
                ),
            }
        ],
        None,
        {
            "type": "object",
            "properties": {
                "diagnostico": {
                    "type": "string",
                },
                "acoes": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "risco": {
                    "type": "string",
                    "enum": [
                        "baixo",
                        "medio",
                        "alto",
                    ],
                },
            },
            "required": [
                "diagnostico",
                "acoes",
                "risco",
            ],
            "additionalProperties": False,
        },
    ),
    (
        "05_tool_call",
        "tool_calling",
        [
            {
                "role": "user",
                "content": (
                    "Qual \xe9 o estado atual do Ollama? Use obrigatoriamente a "
                    "ferramenta dispon\xedvel. N\xe3o invente o resultado da "
                    "ferramenta."
                ),
            }
        ],
        [
            {
                "type": "function",
                "function": {
                    "name": "consultar_status_servico",
                    "description": (
                        "Consulta o estado atual de um servi\xe7o local."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "servico": {
                                "type": "string",
                                "enum": [
                                    "ollama",
                                    "vane",
                                    "searxng",
                                ],
                            }
                        },
                        "required": [
                            "servico",
                        ],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        None,
    ),
    (
        "06_anti_hallucination",
        "hallucination_resistance",
        [
            {
                "role": "user",
                "content": (
                    "Informe o DOI, os autores e os resultados num\xe9ricos do "
                    "artigo 'Holographic Capybara Embeddings for Rural Print "
                    "Shops', publicado em 2026. Se voc\xea n\xe3o puder verificar a "
                    "exist\xeancia do artigo, declare isso claramente e n\xe3o "
                    "invente refer\xeancias."
                ),
            }
        ],
        None,
        None,
    ),
    (
        "07_holo_scenario",
        "holo",
        [
            {
                "role": "user",
                "content": (
                    "O Vane responde em http://127.0.0.1:3000, o Grafana em "
                    "http://100.74.178.62:3000, e o usu\xe1rio diz que n\xe3o encontra "
                    "o Vane no menu. Explique a diferen\xe7a em exatamente quatro "
                    "t\xf3picos. N\xe3o proponha alterar portas, expor Ollama/SearXNG "
                    "\xe0 rede nem ativar Tailscale Funnel."
                ),
            }
        ],
        None,
        None,
    ),
    (
        "08_source_synthesis",
        "source_synthesis",
        [
            {
                "role": "user",
                "content": (
                    "Sintetize em at\xe9 70 palavras, distinguindo servi\xe7o ativo "
                    "de pesquisa comprovadamente funcional.\n"
                    "Fonte A: systemctl informa "
                    "vane-native-searxng.service active.\n"
                    "Fonte B: uma consulta recente retornou zero resultados.\n"
                    "N\xe3o atribua uma causa sem evid\xeancia."
                ),
            }
        ],
        None,
        None,
    ),
    (
        "09_code",
        "code",
        [
            {
                "role": "user",
                "content": (
                    "Escreva uma fun\xe7\xe3o Python 3.12 chamada "
                    "normalizar_slug_ptbr(texto: str) -> str que remova acentos, "
                    "converta para min\xfasculas, substitua sequ\xeancias n\xe3o "
                    "alfanum\xe9ricas por h\xedfen e remova h\xedfens nas extremidades. "
                    "Inclua tr\xeas asserts. Responda somente com um bloco de "
                    "c\xf3digo Python."
                ),
            }
        ],
        None,
        None,
    ),
]


def api(path, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode()

    request = urllib.request.Request(
        API + path,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="GET" if payload is None else "POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def cmd(*args, timeout=120):
    process = subprocess.run(
        args,
        text=True,
        capture_output=True,
        timeout=timeout,
    )

    return {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def gpu():
    process = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
    )

    values = (
        [
            value.strip()
            for value in process.stdout.splitlines()[0].split(",")
        ]
        if process.returncode == 0 and process.stdout.strip()
        else []
    )

    def numeric(index):
        try:
            return float(values[index])
        except (IndexError, TypeError, ValueError):
            return None

    return {
        "vram_mib": numeric(0),
        "temp_c": numeric(1),
        "power_w": numeric(2),
    }


def ram():
    data = {}

    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        data[key] = int(value.strip().split()[0])

    return (data["MemTotal"] - data["MemAvailable"]) / 1024


def monitor(stop_event, samples):
    while not stop_event.wait(0.2):
        sample = gpu()
        sample["ram_mib"] = ram()
        samples.append(sample)


def stream(model, messages, tools, response_format):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": "10m",
        "options": OPTS,
    }

    if tools:
        payload["tools"] = tools

    if response_format:
        payload["format"] = response_format

    request = urllib.request.Request(
        API + "/chat",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.perf_counter()
    first_token = None
    content_parts = []
    thinking_parts = []
    tool_calls = []
    final_response = {}

    with urllib.request.urlopen(request, timeout=900) as response:
        for raw_line in response:
            if not raw_line.strip():
                continue

            event = json.loads(raw_line)
            final_response = event
            message = event.get("message") or {}

            content = message.get("content") or ""
            thinking = (
                message.get("thinking")
                or event.get("thinking")
                or ""
            )
            current_calls = message.get("tool_calls") or []

            if first_token is None and (
                content
                or thinking
                or current_calls
            ):
                first_token = time.perf_counter() - started

            if content:
                content_parts.append(content)

            if thinking:
                thinking_parts.append(thinking)

            if current_calls:
                tool_calls = current_calls

    return {
        "elapsed_s": time.perf_counter() - started,
        "ttft_s": first_token,
        "content": "".join(content_parts),
        "thinking": "".join(thinking_parts),
        "tool_calls": tool_calls,
        "final": final_response,
        "request": payload,
    }


def ns_ms(value):
    try:
        return float(value) / 1e6
    except (TypeError, ValueError):
        return None


def tps(token_count, duration_ns):
    try:
        duration_seconds = float(duration_ns) / 1e9

        if duration_seconds <= 0:
            return None

        return float(token_count) / duration_seconds
    except (TypeError, ValueError):
        return None


def validate(case_id, content, calls):
    stripped = content.strip()

    if case_id == "00_cold_probe":
        return stripped == "PRONTO"

    if case_id == "03_instruction":
        return stripped == "OLLAMA\nVANE\nSEARXNG"

    if case_id == "04_structured_json":
        try:
            parsed = json.loads(stripped)

            return (
                set(parsed)
                == {
                    "diagnostico",
                    "acoes",
                    "risco",
                }
                and isinstance(parsed["acoes"], list)
                and len(parsed["acoes"]) == 2
                and parsed["risco"] == "baixo"
            )
        except (TypeError, ValueError, KeyError):
            return False

    if case_id == "05_tool_call":
        if len(calls) != 1:
            return False

        function = calls[0].get("function") or {}
        arguments = function.get("arguments")

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                arguments = {}

        return (
            function.get("name") == "consultar_status_servico"
            and isinstance(arguments, dict)
            and arguments.get("servico") == "ollama"
        )

    if case_id == "09_code":
        return (
            stripped.startswith("```python")
            and stripped.endswith("```")
            and "def normalizar_slug_ptbr" in stripped
        )

    return None


def stop_loaded():
    for model in api("/ps").get("models", []):
        name = model.get("name") or model.get("model")

        if name:
            cmd(
                "ollama",
                "stop",
                name,
            )


def release(baseline, limit=60):
    deadline = time.time() + limit
    samples = []

    while time.time() < deadline:
        sample = gpu()
        samples.append(sample)

        if (
            baseline is None
            or sample["vram_mib"] is None
            or sample["vram_mib"] <= baseline + 512
        ):
            return True, samples

        time.sleep(1)

    return False, samples


def main():
    OUT.mkdir(parents=True)
    (OUT / "model_show").mkdir()

    prerequisites = {
        "ollama": cmd("systemctl", "is-active", "ollama"),
        "vane-native": cmd(
            "systemctl", "--user", "is-active", "vane-native"
        ),
        "vane-native-searxng": cmd(
            "systemctl", "--user", "is-active",
            "vane-native-searxng"
        ),
    }

    extra_processes = cmd(
        "pgrep",
        "-afi",
        "[l]lama-(server|cli)|[l]m[- ]?[s]tudio",
    )

    (OUT / "prerequisites.json").write_text(
        json.dumps(
            {
                "services": prerequisites,
                "extra_processes": extra_processes,
            },
            indent=2,
        )
    )

    if (
        any(
            result["stdout"].strip() != "active"
            for result in prerequisites.values()
        )
        or extra_processes["stdout"].strip()
    ):
        (OUT / "GATE_FAILED.txt").write_text(
            "Servi\xe7o obrigat\xf3rio inativo ou runtime concorrente ativo.\n"
        )
        return 2

    environment = {
        "ollama_version": cmd(
            "ollama",
            "--version",
        ),
        "ollama_list": cmd(
            "ollama",
            "list",
        ),
        "nvidia_smi": cmd(
            "nvidia-smi",
        ),
        "service_env": cmd(
            "systemctl",
            "show",
            "ollama",
            "-p",
            "Environment",
        ),
    }

    (OUT / "environment.json").write_text(
        json.dumps(
            environment,
            indent=2,
        )
    )

    stop_loaded()
    time.sleep(2)

    rows = []
    halt = False

    for model in MODELS:
        print(
            f"MODEL {model}",
            flush=True,
        )

        key = re.sub(
            r"[^A-Za-z0-9._-]",
            "_",
            model,
        )

        cmd(
            "ollama",
            "stop",
            model,
        )
        time.sleep(2)

        baseline_gpu = gpu()
        baseline_ram = ram()

        try:
            model_show = api(
                "/show",
                {
                    "model": model,
                    "verbose": False,
                },
            )
        except Exception as error:
            model_show = {
                "error": repr(error),
            }

        (OUT / "model_show" / f"{key}.json").write_text(
            json.dumps(
                model_show,
                ensure_ascii=False,
                indent=2,
            )
        )

        for (
            case_id,
            category,
            messages,
            tools,
            response_format,
        ) in CASES:
            print(
                f"  CASE {case_id}",
                flush=True,
            )

            samples = []
            stop_event = threading.Event()
            monitor_thread = threading.Thread(
                target=monitor,
                args=(
                    stop_event,
                    samples,
                ),
                daemon=True,
            )
            monitor_thread.start()

            try:
                response = stream(
                    model,
                    messages,
                    tools,
                    response_format,
                )
                status = "ok"
                error_text = None
            except Exception as error:
                response = {
                    "elapsed_s": None,
                    "ttft_s": None,
                    "content": "",
                    "thinking": "",
                    "tool_calls": [],
                    "final": {},
                    "request": {},
                }
                status = "error"
                error_text = repr(error)

            stop_event.set()
            monitor_thread.join(5)

            final_event = response["final"]

            def peak(key_name):
                return max(
                    (
                        sample[key_name]
                        for sample in samples
                        if sample.get(key_name) is not None
                    ),
                    default=None,
                )

            row = {
                "model": model,
                "case_id": case_id,
                "category": category,
                "status": status,
                "error": error_text,
                "context": OPTS["num_ctx"],
                "elapsed_s": response["elapsed_s"],
                "ttft_s": response["ttft_s"],
                "load_ms": ns_ms(
                    final_event.get("load_duration")
                ),
                "prompt_count": final_event.get(
                    "prompt_eval_count"
                ),
                "prompt_tps": tps(
                    final_event.get("prompt_eval_count"),
                    final_event.get("prompt_eval_duration"),
                ),
                "eval_count": final_event.get(
                    "eval_count"
                ),
                "generation_tps": tps(
                    final_event.get("eval_count"),
                    final_event.get("eval_duration"),
                ),
                "peak_vram_mib": peak("vram_mib"),
                "peak_ram_mib": peak("ram_mib"),
                "peak_temp_c": peak("temp_c"),
                "peak_power_w": peak("power_w"),
                "baseline_vram_mib": baseline_gpu["vram_mib"],
                "baseline_ram_mib": baseline_ram,
                "structural_pass": validate(
                    case_id,
                    response["content"],
                    response["tool_calls"],
                ),
                "content": response["content"],
                "thinking": response["thinking"],
                "tool_calls": response["tool_calls"],
            }

            rows.append(row)

            if (
                case_id == "00_cold_probe"
                and status == "ok"
            ):
                (OUT / f"ps_loaded__{key}.json").write_text(
                    json.dumps(
                        api("/ps"),
                        indent=2,
                    )
                )

            if (
                error_text
                and any(
                    term in error_text.lower()
                    for term in [
                        "out of memory",
                        "cuda error",
                        "xid",
                    ]
                )
            ):
                halt = True
                break

        cmd(
            "ollama",
            "stop",
            model,
        )

        released, release_samples = release(
            baseline_gpu["vram_mib"]
        )

        (OUT / f"vram_release__{key}.json").write_text(
            json.dumps(
                {
                    "released": released,
                    "samples": release_samples,
                },
                indent=2,
            )
        )

        if not released:
            (OUT / "GATE_FAILED.txt").write_text(
                f"VRAM n\xe3o retornou ao baseline ap\xf3s {model}.\n"
            )
            halt = True

        if halt:
            break

    with (OUT / "records.jsonl").open("w") as output:
        for row in rows:
            output.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )

    fields = [
        "model",
        "case_id",
        "category",
        "status",
        "structural_pass",
        "elapsed_s",
        "ttft_s",
        "load_ms",
        "prompt_count",
        "prompt_tps",
        "eval_count",
        "generation_tps",
        "peak_vram_mib",
        "peak_ram_mib",
        "peak_temp_c",
        "peak_power_w",
        "error",
    ]

    with (OUT / "summary.csv").open(
        "w",
        newline="",
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fields,
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row.get(field)
                    for field in fields
                }
            )

    final_state = {
        "ollama_ps": cmd(
            "ollama",
            "ps",
        ),
        "services": {
            "ollama": cmd("systemctl", "is-active", "ollama"),
            "vane-native": cmd(
                "systemctl", "--user", "is-active",
                "vane-native"
            ),
            "vane-native-searxng": cmd(
                "systemctl", "--user", "is-active",
                "vane-native-searxng"
            ),
        },
        "extra_processes": cmd(
            "pgrep",
            "-afi",
            "[l]lama-(server|cli)|[l]m[- ]?[s]tudio",
        ),
        "nvidia_smi": cmd(
            "nvidia-smi",
        ),
        "ollama_journal": cmd(
            "journalctl",
            "-u",
            "ollama",
            "--since",
            START_LOCAL,
            "--no-pager",
        ),
        "kernel_journal": cmd(
            "journalctl",
            "-k",
            "--since",
            START_LOCAL,
            "--no-pager",
        ),
    }

    (OUT / "final_state.json").write_text(
        json.dumps(
            final_state,
            indent=2,
        )
    )

    return 4 if halt else 0


if __name__ == "__main__":
    raise SystemExit(main())
