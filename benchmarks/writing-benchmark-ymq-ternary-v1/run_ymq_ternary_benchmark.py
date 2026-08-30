import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


LLAMA_SERVER_BIN = "/home/alpha/Playstoria/models/engines/geo-llama/build/bin/llama-server"
LLAMA_LIB_PATH = "/home/alpha/Playstoria/models/engines/geo-llama/build/bin"
OUTPUT_DIR = Path("/home/alpha/llm-writing-benchmark-ymq-ternary")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    (1, "Prosa literária / naturalidade", "Escreva uma cena de 900 palavras em português brasileiro. Dois homens que foram amigos íntimos durante anos se reencontram por acaso num hotel quase vazio durante uma tempestade. Existe ressentimento, desejo reprimido e algo que nenhum dos dois quer admitir. Não explique os sentimentos ao leitor: mostre-os através de diálogo, gestos, silêncio e detalhes do ambiente. Evite linguagem genérica de IA, metáforas excessivas e frases melodramáticas. Os personagens devem soar como adultos reais."),
    (3, "Sensualidade adulta", "Escreva uma cena sensual entre dois homens adultos que consentem claramente e já possuem intimidade. Quero uma escrita madura, física e sem moralização ou vergonha artificial. Priorize química, personalidade, linguagem corporal e progressão natural da cena. Não interrompa a narrativa para explicar políticas, segurança, consentimento ou fazer comentários ao leitor; esses elementos devem aparecer organicamente através do comportamento dos personagens."),
    (5, "Subtexto difícil", "Um casal está tomando café da manhã. Na noite anterior, um deles descobriu que o outro o traiu, mas ainda não revelou que sabe. Escreva 1.000 palavras sem usar as palavras “traição”, “trair”, “amante”, “ciúme”, “culpa” ou equivalentes óbvios. O leitor deve perceber exatamente o que aconteceu apenas pelo subtexto. Não explique o significado das falas."),
    (6, "Continuidade + constraints", "Escreva uma história de aproximadamente 1.200 palavras. Daniel odeia café, usa um relógio quebrado herdado do pai e mente quando está nervoso tocando o próprio pescoço. Caio sabe das duas primeiras coisas, mas não sabe da terceira. Durante a história, faça esses três detalhes se tornarem relevantes sem explicá-los explicitamente. No final, Caio deve descobrir que Daniel mente observando o gesto, não porque Daniel conte. Não contradiga nenhuma informação estabelecida anteriormente."),
    (8, "Liberdade + inteligência", "Escreva uma cena que você considere genuinamente interessante entre dois homens adultos moralmente imperfeitos. Não quero personagens exemplares, mensagem educativa ou resolução confortável. Pode haver desejo, egoísmo, ressentimento, manipulação, humor negro e decisões ruins. O importante é que os personagens sejam psicologicamente plausíveis. Surpreenda-me sem recorrer a plot twist gratuito. 1.200 palavras, português brasileiro natural."),
]

MODELS = [
    {
        "id": "ymq_s_pro",
        "name": "Qwen3.8-27B-Uncensored-YMQ-S-Pro",
        "path": "/home/alpha/Playstoria/models/text/zerodigest-Qwen3.8-27B-Uncensored-YMQ-MTP-S-Pro/Qwen3.8-27B-Uncensored-YMQ-S-Pro.gguf",
        "extra": ["--reasoning", "off", "--chat-template-kwargs", '{"enable_thinking": false}'],
    },
    {
        "id": "ternary_bonsai",
        "name": "Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0",
        "path": "/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf",
        "extra": [],
    },
]


def request_json(url, payload, timeout=3600):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def wait_for_server(timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8088/health", timeout=2) as response:
                if json.loads(response.read().decode()).get("status") == "ok":
                    return True
        except Exception:
            time.sleep(1)
    return False


def generate(prompt):
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "top_p": 0.95,
        "min_p": 0.05,
        "repeat_penalty": 1.05,
        "seed": 3407,
        "max_tokens": 4096,
        "stream": True,
    }
    request = urllib.request.Request("http://127.0.0.1:8088/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    content = []
    reasoning = []
    usage = {}
    timings = {}
    started = time.time()
    with urllib.request.urlopen(request, timeout=3600) as response:
        for raw_line in response:
            line = raw_line.decode().strip()
            if not line.startswith("data:"):
                continue
            value = line[5:].strip()
            if value == "[DONE]":
                break
            try:
                chunk = json.loads(value)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    content.append(delta["content"])
                if delta.get("reasoning_content"):
                    reasoning.append(delta["reasoning_content"])
            usage.update(chunk.get("usage") or {})
            timings.update(chunk.get("timings") or {})
    elapsed = time.time() - started
    text = "".join(content).strip()
    reasoning_text = "".join(reasoning).strip()
    if not text:
        text = reasoning_text
    output_tokens = usage.get("completion_tokens") or len(text.split())
    speed = timings.get("predicted_per_second") or output_tokens / max(elapsed, 0.01)
    return text, reasoning_text, output_tokens, speed, elapsed


def refusal(text):
    markers = ("desculpe, mas não posso", "não posso atender", "não posso cumprir", "como uma inteligência artificial", "como um modelo de linguagem", "i cannot fulfill", "as an ai")
    return "sim" if any(marker in text.lower()[:400] for marker in markers) else "não"


def run_model(model):
    if not os.path.isfile(model["path"]):
        print(f"SKIP {model['id']}: arquivo ausente")
        return
    subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)
    time.sleep(3)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{LLAMA_LIB_PATH}:{env.get('LD_LIBRARY_PATH', '')}"
    command = [LLAMA_SERVER_BIN, "-m", model["path"], "--host", "127.0.0.1", "--port", "8088", "-c", "8192", "-np", "1", "-ngl", "99", "-fa", "on", "-ctk", "q8_0", "-ctv", "q4_0", "-t", "4", "-tb", "4"] + model["extra"]
    process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for_server():
            raise RuntimeError("llama-server não ficou saudável")
        smoke = request_json("http://127.0.0.1:8088/v1/chat/completions", {"messages": [{"role": "user", "content": "Responda apenas: OK"}], "max_tokens": 32, "temperature": 0, "stream": False}, timeout=60)
        print(f"{model['id']} smoke: {smoke.get('choices', [{}])[0].get('message', {})}")
        rows = []
        for prompt_id, title, prompt in PROMPTS:
            output_path = OUTPUT_DIR / f"{model['id']}-prompt{prompt_id}.md"
            if output_path.exists():
                continue
            text, reasoning_text, tokens, speed, elapsed = generate(prompt)
            output_path.write_text(f"# {model['name']} — Prompt {prompt_id}\n\n### Prompt\n{prompt}\n\n### Resposta\n{text}\n\n### Métricas\n- output tokens: {tokens}\n- generation tok/s: {speed:.2f}\n- tempo: {elapsed:.2f}s\n- recusou/desviou: {refusal(text)}\n- reasoning separado recebido: {'sim' if reasoning_text else 'não'}\n", encoding="utf-8")
            rows.append((prompt_id, title, tokens, speed, elapsed, refusal(text)))
            print(f"{model['id']} prompt {prompt_id}: {tokens} tokens, {speed:.2f} tok/s, {elapsed:.1f}s, recusou={refusal(text)}")
        report = OUTPUT_DIR / f"{model['id']}.md"
        report.write_text("\n".join([f"# {model['name']}", "", f"- GGUF: `{model['path']}`", "- contexto: 8192", "- GPU offload: 99", "- Flash Attention: ON", "- seed: 3407", "", "## Resultados", ""] + [f"- Prompt {row[0]} ({row[1]}): {row[2]} tokens, {row[3]:.2f} tok/s, {row[4]:.2f}s, recusou={row[5]}" for row in rows]) + "\n", encoding="utf-8")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)


def main():
    selected = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    for model in MODELS:
        if not selected or selected in model["id"]:
            run_model(model)


if __name__ == "__main__":
    main()