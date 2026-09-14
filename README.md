# Hermes Meeting → Action

A public Applied AI builder project for turning meeting context into structured, traceable follow-up actions with as little manual work as possible.

## Problem

Meetings generate decisions, assignments, deadlines, questions, and follow-up messages, but the work of turning those into reliable system updates is still largely manual. Hermes is an experiment in closing that gap with a practical agentic workflow.

## MVP workflow

1. Ingest a meeting transcript, notes, or recap.
2. Extract decisions, action items, owners, due dates, open questions, and follow-ups into a structured schema.
3. Flag missing or low-confidence fields for human review instead of guessing.
4. Route approved actions to the right work systems, starting with tools such as Asana and Notion.
5. Preserve a build/audit trail so every automated action can be traced back to its source.

## Design principles

- **Human control for durable actions**: automation should draft and prepare aggressively, but external writes should be reviewable when risk is meaningful.
- **Low-cost by default**: use deterministic parsing, smaller models, caching, and selective escalation before expensive model calls.
- **Structured outputs first**: actions, decisions, owners, dates, and evidence should be machine-readable.
- **Idempotent integrations**: rerunning the same meeting should not create duplicate tasks or records.
- **Observable behavior**: log what was extracted, what was changed, what failed, and why.
- **Minimal manual input**: the system should infer workflow context from connected tools where safe instead of repeatedly asking the user to re-enter it.

## Initial repository structure

```text
README.md        Project scope, architecture, and usage notes
BUILD_LOG.md     Chronological build decisions, experiments, and results
```

Planned as the project grows:

```text
src/             Core workflow code
prompts/         Versioned extraction and routing prompts
schemas/         Structured output contracts
evals/           Meeting-note evaluation cases and expected outputs
integrations/    External tool adapters
tests/           Automated validation and regression tests
docs/            Architecture and implementation notes
```

## Current status

**2026-09-14:** Repository initialized, the v0.1 structured action contract is defined, and a six-case evaluation baseline is in place. Next milestone is implementing the extraction runner, validating outputs against the schema, and measuring the low-cost extraction path before connecting durable task writes.

## Build log

See [BUILD_LOG.md](BUILD_LOG.md) for the running implementation record.
