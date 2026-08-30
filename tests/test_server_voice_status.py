import json
import os
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server import Handler


class ServerVoiceStatusTests(unittest.TestCase):
    def test_voice_status_uses_one_sentence_asr_mode_without_ws_fields(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 1)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        env = {
            "VOLCENGINE_API_KEY": "test-key",
            "ASR_PUBLIC_WS_URL": "https://commitments-improvements-portland-heating.trycloudflare.com",
        }
        with patch.dict(os.environ, env, clear=True):
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/voice-status", timeout=3) as response:
                body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(body["asr_configured"])
        self.assertEqual(body["asr_mode"], "one_sentence")
        self.assertNotIn("ws_url", body)
        self.assertNotIn("ws_port", body)


if __name__ == "__main__":
    unittest.main()
