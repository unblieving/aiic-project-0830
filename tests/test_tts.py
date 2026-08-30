import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from recall_trainer.tts import synthesize_speech


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class RawResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body.encode("utf-8")


class TtsTests(unittest.TestCase):
    def test_builds_volcano_tts_v3_api_key_request(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse({"code": 0, "data": "audio-data"})

        env = {
            "VOLCENGINE_API_KEY": "test-key",
            "VOLCENGINE_TTS_RESOURCE_ID": "Speech_Synthesis2000000933495388706",
            "VOLCENGINE_TTS_VOICE_TYPE": "BV001_streaming",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = synthesize_speech("你好，这是一段语音测试。")

        body = json.loads(captured["request"].data.decode("utf-8"))
        headers = dict(captured["request"].header_items())
        self.assertEqual(captured["request"].full_url, "https://openspeech.bytedance.com/api/v3/tts/unidirectional")
        self.assertEqual(headers["X-api-key"], "test-key")
        self.assertEqual(headers["X-api-resource-id"], "Speech_Synthesis2000000933495388706")
        self.assertIn("X-api-request-id", headers)
        self.assertEqual(body["req_params"]["text"], "你好，这是一段语音测试。")
        self.assertEqual(body["req_params"]["speaker"], "BV001_streaming")
        self.assertEqual(body["req_params"]["audio_params"]["format"], "mp3")
        self.assertEqual(body["req_params"]["audio_params"]["sample_rate"], 24000)
        self.assertEqual(result["audio_base64"], "audio-data")

    def test_parses_multiline_json_response_and_concatenates_audio_chunks(self):
        body = '\n'.join([
            '{"code":0,"message":"ok"}',
            '{"code":0,"data":"audio-"}',
            '{"code":0,"data":"data"}',
        ])

        with patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test-key"}, clear=True):
            with patch("urllib.request.urlopen", return_value=RawResponse(body)):
                result = synthesize_speech("你好")

        self.assertEqual(result["audio_base64"], "audio-data")

    def test_upstream_business_error_returns_structured_error(self):
        env = {
            "VOLCENGINE_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch(
                "urllib.request.urlopen",
                return_value=FakeResponse({"code": 3001, "message": "invalid voice"}),
            ):
                result = synthesize_speech("你好")

        self.assertEqual(result["error"], "TTS request failed")
        self.assertEqual(result["upstream_status"], 200)
        self.assertIn("invalid voice", result["upstream_message"])

    def test_http_error_returns_upstream_body_and_logs_status(self):
        body = b'{"code":"BadRequest","message":"invalid request","request_id":"req-123"}'
        error = urllib.error.HTTPError(
            url="https://example.test/tts",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(body),
        )

        env = {
            "VOLCENGINE_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env, clear=True):
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
