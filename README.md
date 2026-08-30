# AI Interview Recall Trainer

让存量知识，答得出来。

This MVP helps first-time technical interview candidates practice active recall.
It is a recall coach, not a generic answer generator.

## Core Mechanism

The app enforces this loop:

```text
Cold question -> stuck -> L1/L2/L3 scaffolding -> full re-answer
-> interleaving questions -> surprise retest -> verification
```

The important result is the hint dependency transition, for example:

```text
TCP 三次握手: L2 -> L0
```

## Tech Stack

- Python standard-library HTTP server
- HTML/CSS/JavaScript frontend
- DeepSeek-compatible chat API
- `unittest` for core flow tests

## Local Run

PowerShell:

```powershell
cd C:\Users\Lenovo\aiic-project-0830
$env:DEEPSEEK_API_KEY="your_key"
python server.py
```

The default URL is `http://localhost:80`.

If port 80 requires elevated privileges on your machine, set another port for
local testing:

```powershell
$env:PORT="8080"
python server.py
```

## Environment Variables

- `DEEPSEEK_API_KEY`: DeepSeek API key. If absent, the app uses deterministic
  mock content for demo safety.
- `DEEPSEEK_BASE_URL`: defaults to `https://api.deepseek.com`.
- `DEEPSEEK_MODEL`: defaults to `deepseek-chat`.
- `HOST`: defaults to `0.0.0.0`.
- `PORT`: defaults to `80`.

## Deployment

Run `python server.py` on the server and expose port 80. The provided server IP
for deployment is `43.132.173.100`.

## Scope

P0 only. No login, score dashboard, video, voice, ranking, social sharing,
complex database, RAG, or broad teaching system.
