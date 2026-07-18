#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import re
import sys
import signal
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_DIR = os.environ.get("MODEL_DIR", "")
PORT = int(os.environ.get("PUNCT_PORT", "2027"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if torch.cuda.is_available() else torch.float32

print(f"Loading model from {MODEL_DIR} on {DEVICE}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=DTYPE, device_map="auto")
model.eval()
print("Model loaded.")

SYSTEM_PROMPT = (
    "Restaure APENAS pontuação e capitalização em texto em português. "
    "Não altere palavras, não reescreva frases, não adicione conteúdo. "
    "Não faça raciocínio, não explique. Saída direta apenas."
)
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def restore(text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    try:
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.0,
            do_sample=False,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3,
            pad_token_id=tokenizer.eos_token_id,
        )
    gen = outputs[0][inputs["input_ids"].shape[-1]:]
    out = tokenizer.decode(gen, skip_special_tokens=True).strip()
    out = THINK_RE.sub("", out).strip()
    return out or text


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/restore":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')
            return

        length = int(self.headers.get("content-length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        text = data.get("text", "")
        if not isinstance(text, str) or not text.strip():
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"text": text}).encode())
            return

        try:
            restored = restore(text)
        except Exception as exc:
            sys.stderr.write(f"restore error: {exc}\n")
            restored = text

        body = json.dumps({"text": restored}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)

    def _stop(*_args):
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    print(f"punctuation-restore (generic) listening on 127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
