import requests
import os

session = requests.Session()

# 1. Get CSRF Token
r = session.get("http://127.0.0.1:8000/csrf-token")
data = r.json()
csrf_token = data.get("token")
print("Retrieved CSRF token:", csrf_token)

# 2. Call Edge TTS Plugin generate endpoint
headers = {
    "Content-Type": "application/json",
    "x-csrf-token": csrf_token
}

url = "http://127.0.0.1:8000/api/plugins/edge-tts/generate"
payload = {
    "text": "Olá! Estou testando uma voz local no Arch Linux. Quero uma fala natural em português.",
    "voice": "pt-BR-FranciscaNeural"
}

res = session.post(url, json=payload, headers=headers)
print("Response Status:", res.status_code)
print("Content-Type:", res.headers.get("content-type"))
print("Data size:", len(res.content), "bytes")

out_file = "/tmp/test_edge_tts.webm"
with open(out_file, "wb") as f:
    f.write(res.content)
print(f"Saved audio to {out_file} ({os.path.getsize(out_file)} bytes)")
