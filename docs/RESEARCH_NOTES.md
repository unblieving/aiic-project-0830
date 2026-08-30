# Research Notes

## User Problem

The target user is a student preparing for a first technical internship interview. They often have already learned computer networks, operating systems, databases, Java/JVM, Redis, data structures, and system design basics, but freeze when the interviewer asks a direct question.

The main problem is not always "I never learned this." A frequent failure mode is:

```text
I learned it -> I recognize it when reading -> I cannot actively explain it under pressure
```

This is a recall failure, and it needs a different intervention from long-form teaching.

## Existing Alternatives

General LLM chat:

- Good at explaining concepts.
- Weak at enforcing a training protocol.
- Often gives the answer too early, which can reduce active retrieval effort.

Question banks and interview notes:

- Good for coverage and repetition.
- Weak at diagnosing whether a candidate can answer without cues.
- Usually do not verify whether hints become unnecessary later.

Mock interview tools:

- Good for simulation.
- Often optimize for broad feedback and scoring.
- Can obscure the specific question: did the user recover the knowledge independently?

## Product Hypothesis

If the product forces this loop:

```text
cold question -> progressive hint -> full re-answer -> delayed surprise retest
```

then the user can see whether a previously stuck knowledge point becomes independently retrievable.

## Design Implications

- Do not show the standard answer immediately after the user gets stuck.
- Keep scaffolding progressive: L1 is a light recall cue, L2 narrows the direction, L3 gives a minimal knowledge clue.
- Require full re-answer after recovery.
- Delay retest with interleaving instead of immediately repeating the same question.
- Show concrete transition evidence such as `L2 -> L0`.
- Separate Recall Failure from Knowledge Gap so wrong concepts do not enter the scaffold loop.

## Scope Decisions

Included in MVP:

- Text training loop.
- DeepSeek question generation and judging.
- Knowledge Gap detection and concise standard answer generation.
- Weighted domain sampling from self ratings.
- Optional voice mode for demo richness.

Excluded from MVP:

- Login.
- Long-term history.
- Leaderboard.
- Video.
- Complex RAG or crawler.
- Database.
- Large question-bank ingestion.
