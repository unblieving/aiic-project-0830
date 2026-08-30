import base64
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from recall_trainer.volcengine_one_sentence_asr import OneSentenceASRClient


class OneSentenceAsrTests(unittest.TestCase):
    def test_recognize_uses_api_key_resource_headers_and_audio_payload(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({
                    "result": {"text": "你好，这是一次语音识别测试。"}
                }).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        env = {"VOLCENGINE_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                transcript = OneSentenceASRClient().recognize(b"audio", "audio/webm")

        self.assertEqual(transcript, "你好，这是一次语音识别测试。")
        self.assertEqual(captured["url"], "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash")
        self.assertEqual(captured["headers"]["X-api-key"], "test-key")
        self.assertEqual(captured["headers"]["X-api-resource-id"], "volc.onesentenceasr.common.cn")
        self.assertIn("X-api-request-id", captured["headers"])
        self.assertEqual(captured["body"]["audio"]["data"], base64.b64encode(b"audio").decode("ascii"))
        self.assertEqual(captured["body"]["audio"]["format"], "webm")
        self.assertNotIn("Authorization", captured["headers"])


if __name__ == "__main__":
    unittest.main()
