# Test And Performance Notes

## Automated Verification

Run from the repository root:

```powershell
python -m unittest discover -s tests
node --check static\app.js
```

Current local verification on 2026-08-30:

```text
Ran 57 tests in 2.158s
OK
```

The JavaScript syntax check also exits successfully.

## Covered Areas

- State machine setup and transitions.
- L1/L2/L3 scaffold flow.
- Re-answer and surprise retest handling.
- Recall Failure vs Knowledge Gap routing.
- Weighted domain selection by self rating.
- Result summary schema.
- DeepSeek fallback behavior.
- TTS response handling.
- One-sentence ASR request handling.
- Static regression checks for text submit and TTS lifecycle.

## Manual Smoke Tests

Text mode:

1. Open `http://43.132.173.100`.
2. Choose text mode.
3. Select role/domains/self ratings.
4. Start training.
5. Submit a normal answer.
6. Use "I am stuck" to enter scaffold.
7. Recover and submit a full re-answer.
8. Complete a surprise retest.
9. Verify result page shows Independent Recall, Improved Recall, and Knowledge Gap counts.

Voice mode:

1. Configure `VOLCENGINE_API_KEY`.
2. Open product link in browser.
3. Choose real-time conversation mode.
4. Confirm TTS prompt plays once.
5. Confirm recording starts only after the AI prompt finishes.
6. Submit answer and confirm transcript enters the same `/api/answer` flow.

## Performance Expectations For Demo

The MVP uses a small static frontend and a Python standard-library server, so local page rendering is lightweight. User-perceived latency mainly comes from external APIs:

- DeepSeek question generation and judging.
- Volcengine TTS synthesis.
- Volcengine ASR transcription.

Fallback paths are intentionally included so demo flow can continue if an external service times out or returns an error.

## Stability Notes

- Text mode is the safest live demo path.
- DeepSeek failure falls back to deterministic content.
- TTS failure falls back to showing the prompt text.
- ASR failure falls back to voice-service error handling rather than breaking the whole session.
