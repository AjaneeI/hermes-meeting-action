from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_meeting_action.benchmark import summarize_records
from hermes_meeting_action.extract import extract_meeting_with_metrics
from hermes_meeting_action.scoring import TEXT_THRESHOLD, score_case


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "evals" / "meeting_notes_cases.json"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Evaluation file must contain a JSON list.")
    return payload


def _optional_float_env(name: str) -> float | None:
    value = os.environ.get(name)
    if not value:
        return None
    return float(value)


def _run_metadata(label: str, model: str, text_threshold: float) -> dict[str, Any]:
    return {
        "label": label,
        "model": model,
        "reasoning_effort": os.environ.get("HERMES_REASONING_EFFORT"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_url": os.environ.get("HERMES_BASE_URL"),
        "text_threshold": text_threshold,
        "input_cost_per_million": _optional_float_env("HERMES_INPUT_COST_PER_MILLION"),
        "output_cost_per_million": _optional_float_env("HERMES_OUTPUT_COST_PER_MILLION"),
    }


def run_benchmark(
    *,
    cases_path: Path,
    model: str,
    label: str,
    output_path: Path,
    limit: int | None,
    text_threshold: float,
) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    if limit is not None:
        cases = cases[:limit]

    records: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["id"]
        try:
            result = extract_meeting_with_metrics(case["input"], model=model)
            score = score_case(case["expected_output"], result.payload, text_threshold=text_threshold)
            record = {
                "case_id": case_id,
                "status": "ok",
                "metrics": asdict(result.metrics),
                "score": score,
                "actual_output": result.payload,
            }
            print(
                f"{case_id}: score={score['score']:.4f} "
                f"latency_ms={result.metrics.latency_ms:.2f} "
                f"tokens={result.metrics.total_tokens}"
            )
        except Exception as exc:
            record = {
                "case_id": case_id,
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            print(f"{case_id}: ERROR {type(exc).__name__}: {exc}")
        records.append(record)

    payload = {
        "run": _run_metadata(label, model, text_threshold),
        "summary": summarize_records(records),
        "cases": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Hermes synthetic meeting eval set against one model."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--model", default=os.environ.get("HERMES_MODEL"))
    parser.add_argument("--label", default="benchmark")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--text-threshold", type=float, default=TEXT_THRESHOLD)
    args = parser.parse_args()

    if not args.model:
        parser.error("--model or HERMES_MODEL is required.")
    if not 0 <= args.text_threshold <= 1:
        parser.error("--text-threshold must be between 0 and 1.")

    payload = run_benchmark(
        cases_path=args.cases,
        model=args.model,
        label=args.label,
        output_path=args.output,
        limit=args.limit,
        text_threshold=args.text_threshold,
    )
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
