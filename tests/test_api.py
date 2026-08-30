import unittest

from recall_trainer.api import ApiApp


class ApiTests(unittest.TestCase):
    def test_start_returns_session_and_first_question(self):
        app = ApiApp()

        response = app.handle(
            "POST",
            "/api/session",
            {
                "role": "backend",
                "domains": ["network"],
                "selfRatings": {"network": "high"},
            },
        )

        self.assertEqual(response["status"], "QUESTION")
        self.assertIn("id", response)
        self.assertIn("TCP", response["current"]["question"])

    def test_stuck_returns_l1_scaffold(self):
        app = ApiApp()
        session = app.handle(
            "POST",
            "/api/session",
            {
                "role": "backend",
                "domains": ["network"],
                "selfRatings": {"network": "high"},
            },
        )

        response = app.handle("POST", "/api/stuck", {"sessionId": session["id"]})

        self.assertEqual(response["status"], "SCAFFOLD_L1")
        self.assertIn("scaffold", response)
        self.assertIn("最确定", response["scaffold"])

    def test_unknown_session_returns_error(self):
        app = ApiApp()

        response = app.handle("POST", "/api/answer", {"sessionId": "missing", "answer": "x"})

        self.assertEqual(response["error"], "Session not found.")

    def test_start_falls_back_when_llm_question_generation_crashes(self):
        class BrokenLlm:
            def generate_question(self, role, domain, rating):
                raise RuntimeError("network exploded")

            def generate_scaffold(self, level, question, answer):
                return "scaffold"

            def generate_retest(self, topic, question):
                return "retest"

            def judge_recall(self, question, answer):
                return "L0"

        app = ApiApp(llm=BrokenLlm())

        response = app.handle(
            "POST",
            "/api/session",
            {
                "role": "backend",
                "domains": ["network"],
                "selfRatings": {"network": "high"},
            },
        )

        self.assertEqual(response["status"], "QUESTION")
        self.assertEqual(response["current"]["topic"], "TCP 三次握手")

    def test_start_uses_llm_generated_question(self):
        class FakeLlm:
            def generate_question(self, role, domain, rating):
                return {"topic": "自定义知识点", "question": "这是一道 DeepSeek 生成的问题？"}

            def generate_scaffold(self, level, question, answer):
                return "scaffold"

            def generate_retest(self, topic, question):
                return "retest"

        app = ApiApp(llm=FakeLlm())

        response = app.handle(
            "POST",
            "/api/session",
            {
                "role": "backend",
                "domains": ["network"],
                "selfRatings": {"network": "high"},
            },
        )

        self.assertEqual(response["current"]["topic"], "自定义知识点")
        self.assertEqual(response["current"]["question"], "这是一道 DeepSeek 生成的问题？")

    def test_retest_uses_llm_generated_variant(self):
        class FakeLlm:
            def generate_question(self, role, domain, rating):
                return {"topic": "TCP 三次握手", "question": "TCP 为什么需要三次握手？"}

            def generate_scaffold(self, level, question, answer):
                return "scaffold"

            def generate_retest(self, topic, question):
                return "DeepSeek 生成的 TCP 变式题？"

            def judge_recall(self, question, answer):
                return "L0"

        app = ApiApp(llm=FakeLlm())
        session = app.handle(
            "POST",
            "/api/session",
            {
                "role": "backend",
                "domains": ["network", "os"],
                "selfRatings": {"network": "high", "os": "mid"},
            },
        )
        app.handle("POST", "/api/stuck", {"sessionId": session["id"]})
        app.handle("POST", "/api/scaffold", {"sessionId": session["id"], "answer": "双方确认", "recovered": True})
        app.handle("POST", "/api/answer", {"sessionId": session["id"], "answer": "完整回答"})

        response = app.handle("POST", "/api/answer", {"sessionId": session["id"], "answer": "穿插题回答"})

        self.assertEqual(response["status"], "RETEST")
        self.assertEqual(response["current"]["question"], "DeepSeek 生成的 TCP 变式题？")

    def test_answer_uses_llm_judgment_for_failed_retest(self):
        class FakeLlm:
            def generate_question(self, role, domain, rating):
                return {"topic": "TCP 三次握手", "question": "TCP 为什么需要三次握手？"}

            def generate_scaffold(self, level, question, answer):
                return "scaffold"

            def generate_retest(self, topic, question):
                return "如果只有两次握手会怎样？"

            def judge_recall(self, question, answer):
                return "Failure" if "不会" in answer else "L0"

        app = ApiApp(llm=FakeLlm())
        session = app.handle(
            "POST",
            "/api/session",
            {
                "role": "backend",
                "domains": ["network", "os"],
                "selfRatings": {"network": "high", "os": "mid"},
            },
        )
        app.handle("POST", "/api/stuck", {"sessionId": session["id"]})
        app.handle("POST", "/api/scaffold", {"sessionId": session["id"], "answer": "双方确认", "recovered": True})
        app.handle("POST", "/api/answer", {"sessionId": session["id"], "answer": "完整回答"})
        app.handle("POST", "/api/answer", {"sessionId": session["id"], "answer": "穿插题回答"})

        response = app.handle("POST", "/api/answer", {"sessionId": session["id"], "answer": "不会"})

        self.assertEqual(response["summary"]["attempts"][0]["retest_recall_level"], "Failure")
        self.assertFalse(response["summary"]["attempts"][0]["verified"])


if __name__ == "__main__":
    unittest.main()
