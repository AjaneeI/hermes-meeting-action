# Hermes Build Log

This file records meaningful implementation decisions, experiments, failures, and next steps so the project shows how the system is being built, not just the finished code.

## 2026-09-14 — Repository initialization

### Completed

- Connected the GitHub account to Composio.
- Created the public `AjaneeI/hermes-meeting-action` repository.
- Defined the initial problem: convert meeting artifacts into structured, traceable follow-up work.
- Established design principles around low-cost execution, structured outputs, idempotency, observability, and human control for durable actions.

### First MVP target

Build one end-to-end path that can:

1. accept meeting notes or a transcript,
2. extract decisions and action items,
3. attach evidence from the source text,
4. identify owners and due dates when explicitly supported,
5. flag missing fields rather than inventing them,
6. present a compact approval step, and
7. create approved tasks in a connected work system without duplicates.

### Next build step

Define the structured action schema and create a small evaluation set of real meeting-note examples before wiring the first external write integration.

## 2026-09-14 — Action contract and evaluation baseline

### Completed

- Added `schemas/meeting_action_output.schema.json` as the v0.1 machine-readable extraction contract.
- Added `docs/ACTION_SCHEMA.md` to document extraction rules and review behavior.
- Added `evals/meeting_notes_cases.json` with six realistic synthetic meeting-note cases and schema-valid expected outputs.
- Kept private meeting content out of the public repository while still covering realistic ambiguity and failure modes.
- Updated the README to reflect the new repository structure and current milestone.

### Implementation decisions

- Every decision, action, and open question must carry source evidence.
- Missing owners and due dates remain missing rather than being guessed.
- Relative dates are normalized only when the meeting date makes the result unambiguous.
- Tentative ideas and conditional future possibilities are not treated as committed work.
- Extracted actions begin in a pending approval state before any durable external write.
- Idempotency keys will be generated deterministically downstream instead of by the model.

### Evaluation coverage

The initial cases test explicit ownership, missing ownership, explicit and relative dates, ambiguous dates, decisions without tasks, conditional non-actions, multiple actions, open questions, and human-review triggers.

### Next build step

Implement the first extraction runner with JSON Schema validation, run it against the six-case evaluation set, and compare a low-cost extraction path against a stronger-model fallback before connecting Asana or Notion writes.

## 2026-09-15 — Extraction runner and measurable model benchmark

### Completed

- Added an executable extraction runner using the OpenAI Responses API with strict JSON Schema output.
- Added reusable JSON Schema validation before any downstream action can consume an extraction.
- Added extraction telemetry for latency, input/output/total tokens, reasoning effort, and estimated token cost.
- Added a deterministic field-level scorer that tolerates harmless wording changes while grading owners, dates, evidence, ambiguity state, approvals, review state, and object counts.
- Added `scripts/run_benchmark.py` to execute the six synthetic cases against one model and persist inspectable results.
- Added `scripts/compare_benchmarks.py` to compare a cheap model, a stronger model, and a selective fallback policy.
- Added a scorer smoke test and kept the existing schema-validation CI as a zero-cost regression gate.
- Modernized GitHub Actions to Node 24-compatible action versions.
- Added an opt-in benchmark workflow using `gpt-5.6-luna` as the low-cost default and `gpt-5.6-terra` as the stronger fallback default, with model IDs, reasoning effort, and prices editable at dispatch time.
- Added a `run-model-benchmark` PR label trigger so live model evaluation is intentional rather than spending API budget on every commit.

### Routing decision

Do not escalate merely because a source meeting is missing an owner, due date, or other fact. A stronger model cannot legitimately recover information that was never stated. The current fallback policy escalates extraction errors, low object confidence, or explicit conflict/uncertainty signals instead.

### Evaluation target

For each model and for the routed policy, measure:

- average and minimum field-level correctness,
- number of perfect cases,
- failed cases,
- latency,
- input/output/total tokens,
- estimated dollar cost,
- which cases triggered fallback,
- whether the stronger model improved the failure enough to justify its incremental cost.

### Current gate

Durable Asana or Notion writes remain disabled until the live six-case benchmark establishes a defensible extraction baseline.
