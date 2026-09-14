# Action Schema v0.1

Hermes converts messy meeting artifacts into a small set of structured objects that can be reviewed before anything is written to an external system.

The source of truth for the machine-readable contract is [`schemas/meeting_action_output.schema.json`](../schemas/meeting_action_output.schema.json).

## What Hermes extracts

The first contract has four output groups:

- **Decisions**: conclusions that were actually made in the meeting.
- **Actions**: committed follow-up work, with owner and due-date state kept explicit.
- **Open questions**: unresolved questions or dependencies that still need an answer.
- **Review state**: whether a person should review the extraction before durable writes happen.

Every decision, action, and open question must include source evidence.

## Extraction rules

### 1. Do not turn ideas into decisions

Tentative language such as “maybe,” “possible idea,” or “we could” is not a decision unless the notes show that the group actually chose it.

### 2. Only committed work becomes an action

A future possibility or conditional statement is not an action yet. For example, “If the pilot reaches 20 customers, Priya can draft the scaling plan” should not create a task before the condition is met or the work is explicitly assigned.

### 3. Never invent owners

If no owner is named, `owner.name` stays `null` and `owner.status` becomes `missing`. If the notes point to multiple possible owners, use `ambiguous`.

### 4. Never invent due dates

A due date can be normalized when it is explicit or when a relative phrase is safely anchored to a known meeting date. “By Friday” can be normalized if the meeting date is known. “Next week” stays ambiguous because it does not identify a specific day.

### 5. Preserve evidence

Each extracted object carries at least one supporting quote. This makes the output auditable and gives the approval layer enough context to correct mistakes quickly.

### 6. External writes start as pending

Every extracted action begins with `approval_state: "pending"`. Later workflow steps can approve or reject durable writes to systems such as Asana or Notion.

## Human-review triggers

The first implementation should set `review.needs_human_review` when any material field is missing or ambiguous, when evidence conflicts, or when the extractor is not confident enough to support a durable write.

The schema deliberately does not encode a single global confidence threshold yet. We should measure extractor behavior on the evaluation set before choosing one.

## Idempotency

The model should not invent deduplication identifiers. A downstream deterministic layer should derive an idempotency key from stable source information, such as a source document identifier plus a normalized action fingerprint.

That keeps duplicate prevention out of probabilistic model output.

## Evaluation set

[`evals/meeting_notes_cases.json`](../evals/meeting_notes_cases.json) contains six realistic but synthetic examples. They are intentionally synthetic because this repository is public and private meeting notes should not be committed to it.

The cases cover:

1. explicit owner plus safely resolvable relative due date,
2. missing owner,
3. tentative idea versus committed research task,
4. decision with no action,
5. conditional future work that should not become a task, and
6. multiple actions with a missing due date and an open question.

The expected outputs are schema-valid reference answers. Future evaluation code should compare semantic correctness field by field rather than require exact confidence scores or identical wording.
