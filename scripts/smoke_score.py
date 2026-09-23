from __future__ import annotations

import json
from pathlib import Path

from hermes_meeting_action.scoring import score_case
from scripts.run_benchmark import _summarize


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "meeting_notes_cases.json"


def _check_reference_scorer() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    failed: list[str] = []
    for case in cases:
        result = score_case(case["expected_output"], case["expected_output"])
        if result["score"] != 1.0:
            failed.append(f"{case['id']}: {result['score']}")
    if failed:
        raise SystemExit("Reference scorer smoke test failed:\n" + "\n".join(failed))
    print(f"Scorer smoke test passed for {len(cases)} reference cases.")


def _check_semantic_mismatch_summary() -> None:
    summary = _summarize(
        [
            {
                "case_id": "perfect",
                "status": "ok",
                "score": {"score": 1.0, "failed_fields": []},
                "metrics": {
                    "latency_ms": 10.0,
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "estimated_cost_usd": 0.001,
                },
            },
            {
                "case_id": "schema-valid-but-wrong",
                "status": "ok",
                "score": {
                    "score": 0.8,
                    "failed_fields": ["actions[0].owner.name", "actions[0].due.date"],
                },
                "metrics": {
                    "latency_ms": 20.0,
                    "input_tokens": 12,
                    "output_tokens": 6,
                    "total_tokens": 18,
                    "estimated_cost_usd": 0.002,
                },
            },
        ]
    )
    if summary["cases_with_semantic_mismatches"] != 1:
        raise SystemExit("Semantic mismatch summary did not count the failing case.")
    if summary["failed_field_counts"] != {
        "actions[0].due.date": 1,
        "actions[0].owner.name": 1,
    }:
        raise SystemExit("Semantic mismatch summary did not preserve failed-field counts.")
    print("Semantic mismatch summary smoke test passed.")


def main() -> None:
    _check_reference_scorer()
    _check_semantic_mismatch_summary()


if __name__ == "__main__":
    main()
