import io
import os
import unittest
import urllib.error
from unittest.mock import patch

from recall_trainer.tts import synthesize_speech


class TtsTests(unittest.TestCase):
    def test_http_error_returns_upstream_body_and_logs_status(self):
        body = b'{"code":"BadRequest","message":"invalid request","request_id":"req-123"}'
        error = urllib.error.HTTPError(
            url="https://example.test/tts",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(body),
        )

        with patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test-key"}, clear=True):
            with patch("urllib.request.urlopen", side_effect=error):
                with self.assertLogs("recall_trainer.tts", level="ERROR") as logs:
                    result = synthesize_speech("你好，这是一段语音测试。")

        self.assertEqual(result["error"], "TTS request failed")
        self.assertEqual(result["upstream_status"], 400)
        self.assertEqual(result["upstream_message"], body.decode("utf-8"))
        self.assertIn("[TTS] upstream status=400", logs.output[0])
        self.assertIn("[TTS] response=", logs.output[1])
        self.assertIn("invalid request", logs.output[1])
        self.assertNotIn("test-key", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
