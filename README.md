# AI Interview Recall Trainer

让存量知识，答得出来。

AI Interview Recall Trainer is an MVP for first-time technical interview candidates. It trains active recall, not passive reading: the user must answer a cold question, recover through progressive scaffolding when stuck, re-answer without hints, and later pass a surprise retest.

## Submission

- Product link: http://43.132.173.100
- GitHub repository: https://github.com/unblieving/aiic-project-0830
- Submission package: [docs/SUBMISSION_PACKAGE.md](docs/SUBMISSION_PACKAGE.md)
- Product Memo: [PRODUCT_MEMO.md](PRODUCT_MEMO.md)
- Research notes: [docs/RESEARCH_NOTES.md](docs/RESEARCH_NOTES.md)
- Prototype notes: [docs/PROTOTYPE_NOTES.md](docs/PROTOTYPE_NOTES.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Test and performance notes: [docs/PERFORMANCE_TESTS.md](docs/PERFORMANCE_TESTS.md)

## Core Mechanism

```text
Cold Question -> Recall Failure -> L1/L2/L3 -> Full Re-answer
-> Interleaving -> Surprise Retest -> Verification
```

The key result is a hint-dependency transition, for example:

```text
TCP 三次握手: L2 -> L0
```

The result page separates:

- Independent Recall.
- Improved Recall, such as `L2 -> L0`.
- Knowledge Gap, with a concise DeepSeek-generated standard answer when available.

## Tech Stack

- Python standard-library HTTP server.
- Static HTML/CSS/JavaScript frontend.
- DeepSeek-compatible chat API.
- Optional Volcengine API Key voice services for TTS and one-sentence ASR.
- Python `unittest` for core flow tests.

## Training Strategy

- Each session builds about 5 questions.
- Domain sampling uses self ratings as priority weights: high 50%, medium 40%, low 10%, normalized across selected ratings.
- Self rating only affects domain sampling priority. It does not change question difficulty.
- DeepSeek generates typical high-frequency backend interview questions using common taxonomy such as networks, OS, databases, Java/JVM/concurrency, Redis, data structures, and system design.
- No crawler, database, RAG, login, leaderboard, or large question-bank ingestion is used in this MVP.

## Local Run

PowerShell:

```powershell
cd C:\Users\Lenovo\aiic-project-0830
$env:DEEPSEEK_API_KEY="your_deepseek_key"
python server.py
```

The default URL is `http://localhost:80`.

If port 80 requires elevated privileges on your machine, set another port:

```powershell
$env:PORT="8080"
python server.py
```

## Optional Voice Environment

The product works without voice configuration. To enable voice mode:

```powershell
$env:VOLCENGINE_API_KEY="your_volcengine_api_key"
$env:VOLCENGINE_TTS_RESOURCE_ID="volc.tts.default"
$env:VOLCENGINE_TTS_VOICE_TYPE="BV001_streaming"
$env:VOLCENGINE_ASR_RESOURCE_ID="volc.onesentenceasr.common.cn"
python server.py
```

Do not commit real API keys. `.env` is intentionally ignored.

## Tests

```powershell
cd C:\Users\Lenovo\aiic-project-0830
python -m unittest discover -s tests
node --check static\app.js
```

Latest local verification on 2026-08-30:

```text
Ran 57 tests in 2.158s
OK
```

## Deployment

Run `python server.py` on the server and expose port 80. The current public demo target is:

```text
http://43.132.173.100
```

For voice mode, browsers require a secure context for microphone access. Use a Cloudflare Tunnel or another HTTPS proxy in front of the local HTTP server:

```bash
nohup cloudflared tunnel --url http://127.0.0.1:80 > tunnel.log 2>&1 &
```

Then open the generated `https://...trycloudflare.com` URL for voice-mode testing. Text mode can still be tested through the direct HTTP link.

## Scope

The MVP is intentionally narrow. It does not include login, persistent dashboard, ranking, social sharing, video interview, complex RAG, database-backed history, or broad teaching content.
