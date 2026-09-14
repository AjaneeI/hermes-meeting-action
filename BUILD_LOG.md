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
