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


if __name__ == "__main__":
    unittest.main()
