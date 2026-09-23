# Hermes Meeting → Action

A public Applied AI builder project for turning meeting context into structured, traceable follow-up actions with as little manual work as possible.

## Problem

Meetings generate decisions, assignments, deadlines, questions, and follow-up messages, but the work of turning those into reliable system updates is still largely manual. Hermes is an experiment in closing that gap with a practical agentic workflow.

## MVP workflow

1. Ingest a meeting transcript, notes, or recap.
2. Extract decisions, action items, owners, due dates, open questions, and follow-ups into a structured schema.
3. Flag missing or low-confidence fields for human review instead of guessing.
4. Validate every extraction against the JSON Schema contract.
5. Measure extraction quality, latency, token use, and cost before choosing a model-routing policy.
6. Route approved actions to the right work systems, starting with tools such as Asana and Notion.
7. Preserve a build/audit trail so every automated action can be traced back to its source.

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
src/hermes_meeting_action/ Core extraction, validation, and scoring code
prompts/                   Versioned extraction rules
schemas/                   Structured output contracts
evals/                     Synthetic meeting-note evaluation cases
scripts/                   Validation and benchmark utilities
docs/                      Architecture and implementation notes
.github/workflows/         CI and opt-in model benchmark workflows
```

## Validate the baseline

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python scripts/validate_evals.py
PYTHONPATH=src python scripts/smoke_score.py
```

This validates all expected evaluation outputs against `schemas/meeting_action_output.schema.json` and confirms that the field-level scorer gives the reference outputs a perfect score without making any model calls.

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

Set a model and API key. `HERMES_BASE_URL` is optional for providers that implement the OpenAI Responses API.

```bash
export HERMES_MODEL="your-model-id"
export HERMES_API_KEY="your-api-key"
# export HERMES_BASE_URL="https://provider.example/v1"
# export HERMES_REASONING_EFFORT="none"

PYTHONPATH=src python -m hermes_meeting_action.extract \
  meeting.json \
  --output result.json \
  --metrics-output metrics.json
```

The runner requests strict structured output through the Responses API, validates the result against the repository schema, and fails rather than passing malformed output downstream. Metrics include latency, input/output/total tokens, and estimated cost when token prices are supplied.

## Benchmark a model

The benchmark runner executes all six synthetic cases and records the model output plus field-level quality, latency, token use, and cost metadata.

```bash
export HERMES_API_KEY="your-api-key"
export HERMES_REASONING_EFFORT="none"
export HERMES_INPUT_COST_PER_MILLION="0.20"
export HERMES_OUTPUT_COST_PER_MILLION="1.20"

PYTHONPATH=src python scripts/run_benchmark.py \
  --model gpt-5.6-luna \
  --label low-cost \
  --output results/low-cost.json
```

Run a stronger candidate the same way, then compare them:

```bash
PYTHONPATH=src python scripts/compare_benchmarks.py \
  results/low-cost.json \
  results/stronger.json \
  --json-output results/comparison.json \
  --markdown-output results/comparison.md
```

The routing simulation escalates only when the cheap extraction errors, reports low object confidence, or explicitly signals conflicting/uncertain evidence. Missing facts in the source do not trigger escalation because a stronger model should not be encouraged to invent an owner or deadline.

## GitHub Actions benchmark

`.github/workflows/benchmark.yml` provides an opt-in benchmark for a low-cost model and a stronger fallback. It can be started manually after merge, or from a pull request by applying the `run-model-benchmark` label. The repository must contain an Actions secret named `HERMES_API_KEY` or `OPENAI_API_KEY`.

The default comparison is:

- `gpt-5.6-luna` with reasoning effort `none`
- `gpt-5.6-terra` with reasoning effort `low`

Model IDs, reasoning effort, and token prices are workflow inputs so the benchmark can be updated without changing code when provider pricing or model choices change.

The workflow deliberately fails before any model call when neither supported Actions secret is present. GitHub Actions run `35888789029` exercised that fail-closed path on September 23, 2026: both secret-backed environment variables were empty, so the low-cost and stronger-model steps were skipped. This is configuration evidence, not a model-quality result.

## Current status

**2026-09-23:** baseline schema/scorer validation is green in Actions run `35884079235`. The benchmark runner also reports semantic mismatch cases and failed-field frequencies so schema-valid but wrong output is visible. The first live benchmark trigger, run `35888789029`, stopped at credential preflight because neither `HERMES_API_KEY` nor `OPENAI_API_KEY` is configured; no model calls ran and no quality/cost conclusion is claimed. Durable Asana or Notion writes remain intentionally out of scope until extraction quality is measured.

## Upstream contribution path

This project is also the intended vehicle for demonstrating external technical contribution once the standalone v0 is stable.

The target sequence is:

1. Build and validate the standalone workflow.
2. Exercise it on real meeting-note examples with human approval around durable writes.
3. Package the reusable portion as a focused Hermes skill, plugin, documentation contribution, test, or integration improvement.
4. Submit the smallest legitimate upstream contribution that can be independently reviewed.
5. Treat any accepted upstream contribution as evidence that the work has been evaluated by engineers outside this repository.

This is not a reason to expand scope early. The contribution path starts only after the extraction runner, schema validation, evaluation baseline, logging, and idempotency behavior are working.

Relevant upstream references:

- Hermes contribution guide: https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md
- Hermes plugin catalog policy: https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md

## Build log

See [BUILD_LOG.md](BUILD_LOG.md) for the running implementation record.
