# AI Interview Recall Trainer MVP Spec

This repository implements the MVP described in the attached product spec.
The product source of truth is: "AI 面试知识提取训练器 - MVP Spec".

## Product Thesis

让存量知识，答得出来。

The MVP is a knowledge recall trainer for students preparing for their first
technical interviews. It is not a broad mock interview platform and not a
teaching system.

## Target User

The primary user is an undergraduate student preparing for a first large-tech
internship interview, with basic CS knowledge but limited interview output
practice.

## Core Loop

The required P0 loop is:

```text
Cold Question
Independent Recall
Recall Failure
Progressive Scaffolding
Full Re-answer
Interleaving
Surprise Retest
Verification
```

## P0 Scope

- Setup: role, 1-3 domains, self rating for each selected domain.
- Training: generated questions, text answers, stuck button, L1/L2/L3 coaching,
  mandatory full re-answer.
- Verification: record recall level, ask interleaving questions, generate a
  variant retest, compare first recall and retest recall.
- Result: show topic, self rating, first recall level, retest recall level, and
  the `Lx -> Ly` transition.

## Explicit Non-goals

No login, dashboard, score, ranking, social sharing, video, voice, emotion
analysis, complex RAG, multi-agent architecture, or complex database in this
MVP.

## LLM Boundary

The program controls state. The LLM only helps with content:

- question generation
- recall sufficiency judgment
- L1/L2/L3 coaching text
- retest question generation

The LLM must not decide the business flow.

## API Provider

Use DeepSeek-compatible API calls. Do not use OpenAI APIs.
