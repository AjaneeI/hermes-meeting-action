# Hermes Meeting → Action

A public Applied AI builder project for turning meeting context into structured, traceable follow-up actions with as little manual work as possible.

## Problem

Meetings generate decisions, assignments, deadlines, questions, and follow-up messages, but the work of turning those into reliable system updates is still largely manual. Hermes is an experiment in closing that gap with a practical agentic workflow.

## MVP workflow

1. Ingest a meeting transcript, notes, or recap.
2. Extract decisions, action items, owners, due dates, open questions, and follow-ups into a structured schema.
3. Flag missing or low-confidence fields for human review instead of guessing.
4. Validate every extraction against the JSON Schema contract.
5. Route approved actions to the right work systems, starting with tools such as Asana and Notion.
6. Preserve a build/audit trail so every automated action can be traced back to its source.

## Design principles

- **Human control for durable actions**: automation should draft and prepare aggressively, but external writes should be reviewable when risk is meaningful.
- **Low-cost by default**: use deterministic parsing, smaller models, caching, and selective escalation before expensive model calls.
- **Structured outputs first**: actions, decisions, owners, dates, and evidence should be machine-readable.
- **Idempotent integrations**: rerunning the same meeting should not create duplicate tasks or records.
- **Observable behavior**: log what was extracted, what was changed, what failed, and why.
- **Minimal manual input**: the system should infer workflow context from connected tools where safe instead of repeatedly asking the user to re-enter it.

## Repository structure

```text
README.md                  Project scope and usage notes
BUILD_LOG.md               Chronological build decisions and results
src/hermes_meeting_action/ Core extraction + validation code
prompts/                   Versioned extraction rules
schemas/                   Structured output contracts
evals/                     Synthetic meeting-note evaluation cases
scripts/                   Local validation utilities
docs/                      Architecture and implementation notes
.github/workflows/         CI checks
```

## Validate the baseline

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/validate_evals.py
```

This validates all expected evaluation outputs against `schemas/meeting_action_output.schema.json` without making any model calls.

## Run an extraction

Create an input file such as `meeting.json`:

```json
{
  "source_id": "meeting-001",
  "title": "Product sync",
  "occurred_on": "2026-09-15",
  "notes": "Maya: We will ship the pilot Friday. Leo, update the checklist by Thursday."
}
```

Set a model and API key. `HERMES_BASE_URL` is optional for OpenAI-compatible providers.

```bash
export HERMES_MODEL="your-model-id"
export HERMES_API_KEY="your-api-key"
# export HERMES_BASE_URL="https://provider.example/v1"

PYTHONPATH=src python -m hermes_meeting_action.extract meeting.json --output result.json
```

The runner requests strict structured output, validates the result against the repository schema, and fails rather than passing malformed output downstream.

## Current status

**2026-09-15:** v0.1 now has a machine-readable schema, six-case synthetic eval baseline, versioned extraction prompt, provider-configurable CLI runner, schema validation helper, and CI baseline validation. The next milestone is running the six cases through a low-cost model, measuring field-level accuracy/cost/latency, and testing a stronger-model fallback before any durable Asana or Notion writes.

## Build log

See [BUILD_LOG.md](BUILD_LOG.md) for the running implementation record.
