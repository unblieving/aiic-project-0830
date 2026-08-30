import os
import unittest
from unittest.mock import patch

from recall_trainer.llm import RecallCoachClient


class LlmTests(unittest.TestCase):
    def test_uses_mock_question_when_deepseek_key_is_absent(self):
        with patch.dict(os.environ, {}, clear=True):
            client = RecallCoachClient()

        result = client.generate_question("backend", "network", "high")

        self.assertEqual(result["topic"], "TCP 三次握手")
        self.assertIn("TCP", result["question"])

    def test_l1_prompt_contains_no_knowledge_content(self):
        client = RecallCoachClient(api_key="")

        result = client.generate_scaffold("L1", "TCP 为什么需要三次握手？", "")

        self.assertIn("最确定", result)
        self.assertNotIn("发送和接收能力", result)

    def test_falls_back_to_minimal_cue_when_api_call_fails(self):
        client = RecallCoachClient(api_key="test-key")

        with patch.object(client, "_call_deepseek", side_effect=TimeoutError("slow")):
            result = client.generate_scaffold(
                "L3",
                "TCP 为什么需要三次握手？",
                "和双方确认有关",
            )

        self.assertIn("方向", result)
        self.assertLess(len(result), 80)


if __name__ == "__main__":
    unittest.main()
