import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticTextSubmitTests(unittest.TestCase):
    def test_text_submit_has_observable_flow_and_result_state(self):
        app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("[SUBMIT] clicked", app_js)
        self.assertIn("[SUBMIT] sending type=", app_js)
        self.assertIn("[SUBMIT] response status=", app_js)
        self.assertIn("[SUBMIT] response body=", app_js)
        self.assertIn('payload.status === "RESULT"', app_js)


if __name__ == "__main__":
    unittest.main()
