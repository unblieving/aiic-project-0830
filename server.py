from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from recall_trainer.api import ApiApp
from recall_trainer.volcengine_asr import is_asr_configured, get_ws_port
from recall_trainer.tts import is_tts_configured


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
APP = ApiApp()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/voice-status":
            self._send_json({
                "asr_configured": is_asr_configured(),
                "tts_configured": is_tts_configured(),
                "ws_port": get_ws_port(),
            })
            return
        if parsed.path.startswith("/api/"):
            self._send_json(APP.handle("GET", self.path))
            return
        self._send_static(parsed.path)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON."}, status=400)
            return
        response = APP.handle("POST", urlparse(self.path).path, payload)
        self._send_json(response, status=400 if "error" in response else 200)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        file_path = (STATIC_DIR / relative).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "80"))

    # Start WebSocket ASR server in background thread
    ws_port = get_ws_port()
    try:
        from recall_trainer.ws_handler import start_ws_server
        start_ws_server(ws_port)
    except Exception as exc:
        print(f"Warning: WebSocket ASR server failed to start: {exc}")

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving recall trainer on http://{host}:{port}")
    if is_asr_configured():
        print(f"Voice ASR WebSocket on ws://{host}:{ws_port}/ws/asr")
    else:
        print("Voice ASR not configured (set VOLCENGINE_API_KEY to enable)")
    server.serve_forever()


if __name__ == "__main__":
    main()
