# Architecture

## System Overview

```mermaid
flowchart TD
    Browser[Browser SPA]
    Server[Python HTTP Server]
    Api[ApiApp]
    State[Deterministic State Machine]
    LLM[DeepSeek-compatible API]
    TTS[Volcengine TTS]
    ASR[Volcengine One-sentence ASR]

    Browser -->|static files| Server
    Browser -->|POST /api/session| Server
    Browser -->|POST /api/answer| Server
    Browser -->|POST /api/stuck, /api/scaffold| Server
    Browser -->|POST /api/tts| Server
    Browser -->|POST /api/asr| Server

    Server --> Api
    Api --> State
    Api -->|question, judge, scaffold, retest, answer| LLM
    Server --> TTS
    Server --> ASR
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> QUESTION
    QUESTION --> SCAFFOLD_L1: recall failure
    QUESTION --> QUESTION: L0 or knowledge gap, next first attempt
    SCAFFOLD_L1 --> SCAFFOLD_L2: still stuck
    SCAFFOLD_L2 --> SCAFFOLD_L3: still stuck
    SCAFFOLD_L1 --> REANSWER: recovered
    SCAFFOLD_L2 --> REANSWER: recovered
    SCAFFOLD_L3 --> REANSWER: recovered or final hint
    REANSWER --> QUESTION: correct re-answer, interleaving
    REANSWER --> QUESTION: knowledge gap
    QUESTION --> RETEST: delayed surprise retest due
    RETEST --> QUESTION: more pending first attempts
    RETEST --> RESULT: no pending attempts
    QUESTION --> RESULT: no pending attempts or retests
```

## Responsibility Split

Program-controlled:

- Session creation.
- Question order.
- Scaffold level transitions.
- Re-answer requirement.
- Retest scheduling.
- Result summary shape.

LLM-assisted:

- High-frequency backend interview question generation.
- Recall sufficiency judgment.
- L1/L2/L3 scaffold text.
- Retest question generation.
- Concise Knowledge Gap answer.

## API Surface

- `POST /api/session`: create a training session.
- `POST /api/answer`: submit text or voice transcript answer.
- `POST /api/stuck`: enter L1 scaffold.
- `POST /api/scaffold`: advance scaffold or mark recovery.
- `GET /api/result?sessionId=...`: fetch final summary.
- `GET /api/voice-status`: report optional voice service configuration.
- `POST /api/tts`: synthesize interview prompt audio.
- `POST /api/asr`: transcribe a recorded voice answer.

## Deployment Shape

```text
User browser
-> public HTTP endpoint http://43.132.173.100
-> Python server on port 80
-> DeepSeek API for LLM content
-> Volcengine API for optional voice services
```

No database is required for the MVP. Sessions are held in memory because the competition demo only needs a short interactive flow.
