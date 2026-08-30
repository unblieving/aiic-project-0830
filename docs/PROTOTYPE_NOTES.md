# Prototype Notes

## Prototype Goal

The prototype is the running web application itself. It prioritizes a complete recall-training path over a large feature set.

## Primary User Flow

```text
Mode selection
-> Setup role and 1-3 domains
-> Rate familiarity for each domain
-> Start training
-> Answer cold question
-> If stuck, enter L1/L2/L3 scaffold
-> Full re-answer
-> Interleaving question
-> Surprise retest
-> Result summary
```

## Important Screens

Setup:

- Role selection.
- Domain selection.
- Self rating per selected domain.

Training:

- Current question number.
- Current question or voice prompt status.
- Text answer area or voice answer state.
- "I am stuck" route into scaffolding.

Scaffolding:

- L1/L2/L3 hint content.
- Recovery action.
- Required re-answer state after recovery.

Retest:

- Variant question for a previously scaffolded concept.
- No repeated scaffold loop in the MVP retest path.

Result:

- Total trained questions.
- Independent Recall.
- Improved Recall.
- Knowledge Gap.
- Per-topic transition such as `L2 -> L0`.
- Concise answer for Knowledge Gap items.

## Interaction Principles

- The app should feel like a training tool, not a content library.
- The user should do the retrieval work before seeing the answer.
- The result page should make the learning signal inspectable.
- The demo path should remain usable even when external APIs fail.
