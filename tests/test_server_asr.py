import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server import Handler


class ServerAsrTests(unittest.TestCase):
    def _server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 1)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def test_asr_success_accepts_raw_audio_body(self):
        server = self._server()
        audio = b"webm-audio-bytes"
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/api/asr",
            data=audio,
            headers={"Content-Type": "audio/webm;codecs=opus"},
            method="POST",
        )

        with patch("recall_trainer.volcengine_one_sentence_asr.recognize_audio", return_value="你好，这是一次语音识别测试。") as recognize:
            with urllib.request.urlopen(request, timeout=3) as response:
                body = json.loads(response.read().decode("utf-8"))

        recognize.assert_called_once_with(audio, "audio/webm;codecs=opus")
        self.assertEqual(response.status, 200)
        self.assertEqual(body, {"ok": True, "transcript": "你好，这是一次语音识别测试。"})

    def test_asr_empty_body_returns_structured_error(self):
        server = self._server()
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/api/asr",
            data=b"",
            headers={"Content-Type": "audio/webm"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)

        self.assertEqual(caught.exception.code, 400)
        body = json.loads(caught.exception.read().decode("utf-8"))
        self.assertEqual(body, {"ok": False, "error": "empty audio body"})


if __name__ == "__main__":
    unittest.main()
