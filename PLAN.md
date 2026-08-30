# MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P0 recall training loop from the Spec with minimum engineering scope.

**Architecture:** A small Python standard-library HTTP server serves static UI and JSON APIs. A deterministic state machine controls setup, questions, scaffolding, re-answer, interleaving, retest, and results. DeepSeek calls are isolated in one module and fall back to mock content.

**Tech Stack:** Python 3 standard library, HTML, CSS, JavaScript, unittest.

---

## File Structure

- `server.py`: HTTP server, static file serving, JSON route dispatch.
- `recall_trainer/state_machine.py`: deterministic P0 training state and transitions.
- `recall_trainer/llm.py`: DeepSeek API integration and mock fallback content.
- `recall_trainer/prompts.py`: all LLM prompts in one place.
- `static/index.html`: single-page app shell.
- `static/styles.css`: focused visual styling for setup, training, and results.
- `static/app.js`: browser state, API calls, and UI rendering.
- `tests/test_state_machine.py`: state machine behavior tests.
- `.env.example`: documented environment variables.
- `README.md`: product goal, mechanism, stack, local run, deployment notes.
- `HANDOFF.md`: current completion state and safe next steps.

## Phase Order

- [ ] Phase 0: repository docs, env example, initial commit.
- [ ] Phase 1: mock static product flow.
- [ ] Phase 2: deterministic training state machine.
- [ ] Phase 3: DeepSeek integration with fallback.
- [ ] Phase 4: verification and result presentation.
- [ ] Phase 5: robustness checks.
- [ ] Phase 6: restrained visual polish after P0 stability.
- [ ] Phase 7: deployment notes for port 80 and public URL.

## TDD Tasks

### Task 1: State Machine Setup

- [ ] Write failing tests for starting a session with role, 1-3 domains, and self ratings.
- [ ] Implement `start_session`.
- [ ] Run tests and commit.

### Task 2: Scaffolding Flow

- [ ] Write failing tests for stuck -> L1 -> L2 -> L3 -> re-answer.
- [ ] Implement explicit transitions.
- [ ] Run tests and commit.

### Task 3: Retest Scheduling

- [ ] Write failing tests for marking a coached topic for delayed retest after interleaving.
- [ ] Implement interleaving counter and variant retest activation.
- [ ] Run tests and commit.

### Task 4: Verification Result

- [ ] Write failing tests for `L2 -> L0` result records.
- [ ] Implement result summary.
- [ ] Run tests and commit.

### Task 5: DeepSeek Boundary

- [ ] Write tests for API fallback when key is absent or API fails.
- [ ] Implement DeepSeek-compatible client with strict prompts.
- [ ] Run tests and commit.

### Task 6: UI Integration

- [ ] Connect setup, answer submission, stuck flow, re-answer, retest, and result pages.
- [ ] Verify manually in the browser.
- [ ] Commit after the P0 demo path works.
