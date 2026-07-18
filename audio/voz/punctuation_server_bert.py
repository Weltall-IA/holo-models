import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bert_restore import RestorePuncts

MODEL = RestorePuncts(use_cuda=True)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/restore":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')
            return

        length = int(self.headers.get("content-length", 0))
        payload = self.rfile.read(length)
        data = json.loads(payload or "{}")
        text = data.get("text", "")
        if not isinstance(text, str) or not text.strip():
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"text": text}).encode())
            return

        try:
            restored = MODEL.restore_puncts(text)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"restore error: {exc}\n")
            restored = text

        body = json.dumps({"text": restored}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        sys.stderr.write("%s\n" % (format % args))


def main():
    host = os.environ.get("PUNCTUATION_HOST", "127.0.0.1")
    port = int(os.environ.get("PUNCTUATION_PORT", "2024"))
    server = HTTPServer((host, port), Handler)

    def _stop(*_args):
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    print(f"punctuation-restore (bert) listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
