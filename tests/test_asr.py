import asyncio
import os
import sys
import types
import unittest
from unittest.mock import patch

from recall_trainer.volcengine_asr import VolcengineASRClient


class AsrTests(unittest.TestCase):
    def test_connect_uses_api_key_headers_without_authorization(self):
        captured = {}

        async def fake_connect(endpoint, **kwargs):
            captured["endpoint"] = endpoint
            captured["headers"] = kwargs["additional_headers"]
            return object()

        fake_websockets = types.SimpleNamespace(connect=fake_connect)
        env = {
            "VOLCENGINE_API_KEY": "test-key",
            "VOLCENGINE_ASR_ENDPOINT": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
            "VOLCENGINE_ASR_RESOURCE_ID": "volc.bigasr.sauc.duration",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch.dict(sys.modules, {"websockets": fake_websockets}):
                asyncio.run(VolcengineASRClient().connect())

        self.assertEqual(captured["endpoint"], "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel")
        self.assertEqual(captured["headers"]["X-Api-Key"], "test-key")
        self.assertEqual(captured["headers"]["X-Api-Resource-Id"], "volc.bigasr.sauc.duration")
        self.assertIn("X-Api-Request-Id", captured["headers"])
        self.assertEqual(captured["headers"]["X-Api-Sequence"], "-1")
        self.assertNotIn("Authorization", captured["headers"])


if __name__ == "__main__":
    unittest.main()
