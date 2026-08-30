# AIIC Submission Package

## Submission Links

- Product link: http://43.132.173.100
- GitHub repository: https://github.com/unblieving/aiic-project-0830
- Product Memo: [PRODUCT_MEMO.md](../PRODUCT_MEMO.md)
- Demo script: [DEMO_SCRIPT.md](../DEMO_SCRIPT.md)

## One-line Pitch

AI Interview Recall Trainer helps first-time technical interview candidates turn knowledge they have already learned into answers they can actively recall under interview pressure.

## What To Show In The Demo

1. Start from the mode selection page and choose text mode for the most stable path.
2. Select backend interview domains such as computer networks, operating systems, databases, Java/JVM/concurrency, Redis, data structures, or system design.
3. Trigger a cold question.
4. Use "I am stuck" to enter L1/L2/L3 progressive scaffolding.
5. Recover and perform the required full re-answer without seeing the scaffold.
6. Continue through interleaving questions.
7. Show the surprise retest.
8. End on the result page, highlighting Independent Recall, Improved Recall, and Knowledge Gap.

## Core Product Evidence

The product is not a generic interview chatbot. The state machine enforces a recall-training protocol:

```text
Cold Question -> Recall Failure -> L1/L2/L3 -> Full Re-answer
-> Interleaving -> Surprise Retest -> Verification
```

The final evidence is a change in hint dependency, for example `L2 -> L0`, rather than a vague interview score.

## Supporting Materials

- Research notes: [docs/RESEARCH_NOTES.md](RESEARCH_NOTES.md)
- Prototype notes and user flow: [docs/PROTOTYPE_NOTES.md](PROTOTYPE_NOTES.md)
- Architecture diagram: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- Test and performance notes: [docs/PERFORMANCE_TESTS.md](PERFORMANCE_TESTS.md)
- Submission checklist: [SUBMISSION_CHECKLIST.md](../SUBMISSION_CHECKLIST.md)

## Technical Summary

- Backend: Python standard-library HTTP server.
- Frontend: static HTML/CSS/JavaScript.
- LLM: DeepSeek-compatible API only, with deterministic fallback.
- Voice: optional Volcengine API Key integration for TTS and one-sentence ASR fallback.
- Persistence: in-memory session state for MVP demo simplicity.
- Tests: Python `unittest` suite plus JavaScript syntax check.

## Demo Reliability Notes

- Text mode is the primary MVP path and does not depend on voice services.
- If `DEEPSEEK_API_KEY` is missing or unavailable, deterministic mock content keeps the recall loop usable.
- If voice TTS/ASR fails, the app falls back to text display/submission so the demo can continue.
- No `.env`, API keys, tokens, or private credentials are committed.
