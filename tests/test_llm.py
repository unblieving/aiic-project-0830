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

    def test_generate_question_uses_deepseek_response_when_api_key_exists(self):
        client = RecallCoachClient(api_key="test-key")

        with patch.object(client, "_call_deepseek", return_value='{"topic":"缓存","question":"缓存为什么有用？"}'):
            result = client.generate_question("backend", "os", "mid")

        self.assertEqual(result["topic"], "缓存")
        self.assertEqual(result["question"], "缓存为什么有用？")

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

    def test_generate_retest_uses_deepseek_response_when_api_key_exists(self):
        client = RecallCoachClient(api_key="test-key")

        with patch.object(client, "_call_deepseek", return_value='{"question":"DeepSeek 变式题？"}'):
            result = client.generate_retest("TCP 三次握手", "TCP 为什么需要三次握手？")

        self.assertEqual(result, "DeepSeek 变式题？")

    def test_judges_obvious_failure_as_failure(self):
        client = RecallCoachClient(api_key="")

        result = client.judge_recall("TCP 为什么需要三次握手？", "不知道")

        self.assertEqual(result, "recall_failure")

    def test_retrieval_failure_phrases_do_not_call_deepseek(self):
        client = RecallCoachClient(api_key="test-key")
        answers = [
            "我不知道",
            "这个我忘了",
            "好像学过，但是现在想不起来",
            "I don't know",
        ]

        with patch.object(client, "_call_deepseek") as call:
            for answer in answers:
                self.assertEqual(client.judge_recall("TCP 为什么需要三次握手？", answer), "recall_failure")

        call.assert_not_called()

    def test_judges_substantive_answer_as_l0(self):
        client = RecallCoachClient(api_key="")

        result = client.judge_recall("TCP 为什么需要三次握手？", "确认双方发送和接收能力，避免历史连接")

        self.assertEqual(result, "L0")

    def test_judges_wrong_direction_as_knowledge_gap(self):
        client = RecallCoachClient(api_key="")

        result = client.judge_recall("TCP 为什么需要三次握手？", "TCP 三次握手是为了让数据库索引更快")

        self.assertEqual(result, "knowledge_gap")

    def test_judges_tcp_encryption_claim_as_knowledge_gap(self):
        client = RecallCoachClient(api_key="")

        result = client.judge_recall("TCP 为什么需要三次握手？", "TCP 三次握手是为了加密数据")

        self.assertEqual(result, "knowledge_gap")

    def test_judges_gibberish_as_knowledge_gap(self):
        client = RecallCoachClient(api_key="")

        for answer in ["哈哈", "随便", "asdf", "111", "房价跌降发哦", "我乱写的"]:
            with self.subTest(answer=answer):
                self.assertEqual(client.judge_recall("TCP 为什么需要三次握手？", answer), "knowledge_gap")

    def test_standard_answer_fallback_is_concise(self):
        client = RecallCoachClient(api_key="")

        result = client.generate_standard_answer("TCP 三次握手", "TCP 为什么需要三次握手？")

        self.assertIn("正确结论", result)
        self.assertIn("关键知识点", result)
        self.assertLess(len(result), 220)

    def test_reference_answer_fallback_returns_answer_and_key_points(self):
        client = RecallCoachClient(api_key="")

        result = client.generate_reference_answer("TCP 三次握手", "TCP 为什么需要三次握手？")

        self.assertIn("reference_answer", result)
        self.assertIn("key_points", result)
        self.assertGreaterEqual(len(result["key_points"]), 2)
        self.assertLessEqual(len(result["key_points"]), 4)

    def test_judge_accepts_deepseek_knowledge_gap(self):
        client = RecallCoachClient(api_key="test-key")

        with patch.object(client, "_call_deepseek", return_value='{"recall_type":"knowledge_gap"}'):
            result = client.judge_recall("TCP 为什么需要三次握手？", "索引")

        self.assertEqual(result, "knowledge_gap")


if __name__ == "__main__":
    unittest.main()
