import base64
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server import Handler


class ServerTtsTests(unittest.TestCase):
    def test_tts_success_returns_audio_mpeg_bytes(self):
        audio_bytes = b"\xff\xfb\x90\x64audio"
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)

        payload = {"text": "你好"}
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/api/tts",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with patch("recall_trainer.tts.synthesize_speech", return_value={
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "format": "mp3",
        }):
            with urllib.request.urlopen(request, timeout=3) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type")

        self.assertEqual(response.status, 200)
        self.assertEqual(content_type, "audio/mpeg")
        self.assertEqual(body, audio_bytes)


if __name__ == "__main__":
    unittest.main()
