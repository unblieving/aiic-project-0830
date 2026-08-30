import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticTtsLifecycleTests(unittest.TestCase):
    def test_tts_wait_does_not_treat_pause_as_completion(self):
        app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("audio.onpause", app_js)
        self.assertIn('"ended"', app_js)
        self.assertIn('"error"', app_js)
        self.assertIn('"tts-cancelled"', app_js)
        self.assertIn("skip stale cleanup", app_js)
        self.assertIn("[TTS DIAG]", app_js)


if __name__ == "__main__":
    unittest.main()
