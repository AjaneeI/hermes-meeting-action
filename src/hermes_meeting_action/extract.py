from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from .validator import validate_output


ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "extraction_system.txt"
SCHEMA_PATH = ROOT / "schemas" / "meeting_action_output.schema.json"


@dataclass(frozen=True)
class ExtractionMetrics:
    model: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None


@dataclass(frozen=True)
class ExtractionResult:
    payload: dict[str, Any]
    metrics: ExtractionMetrics


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _optional_env_float(name: str) -> float | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number when set.") from exc


def _estimate_cost(
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    input_rate = _optional_env_float("HERMES_INPUT_COST_PER_MILLION")
    output_rate = _optional_env_float("HERMES_OUTPUT_COST_PER_MILLION")
    if input_rate is None or output_rate is None:
        return None
    if input_tokens is None or output_tokens is None:
        return None
    return round(
        (input_tokens / 1_000_000) * input_rate
        + (output_tokens / 1_000_000) * output_rate,
        8,
    )


def build_user_prompt(meeting: dict[str, Any]) -> str:
    required = {"source_id", "notes"}
    missing = sorted(required.difference(meeting))
    if missing:
        raise ValueError(f"Meeting input is missing required fields: {', '.join(missing)}")

    return (
        "Extract the following meeting artifact into the required JSON contract.\n\n"
        f"source_id: {meeting['source_id']}\n"
        f"title: {meeting.get('title')}\n"
        f"occurred_on: {meeting.get('occurred_on')}\n\n"
        "notes:\n"
        f"{meeting['notes']}"
    )


def extract_meeting_with_metrics(
    meeting: dict[str, Any],
    *,
    model: str | None = None,
) -> ExtractionResult:
    model_name = model or os.environ.get("HERMES_MODEL")
    if not model_name:
        raise RuntimeError("Set HERMES_MODEL or pass model=... to choose a model.")

    api_key = os.environ.get("HERMES_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set HERMES_API_KEY or OPENAI_API_KEY.")

    base_url = os.environ.get("HERMES_BASE_URL")
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    schema = _read_json(SCHEMA_PATH)
    system_prompt = _read_text(SYSTEM_PROMPT_PATH)

    started = time.perf_counter()
    response = client.responses.create(
        model=model_name,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(meeting)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "hermes_meeting_action_output",
                "strict": True,
                "schema": schema,
            }
        },
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    content = response.output_text
    if not content:
        raise RuntimeError("Model returned an empty response.")

    payload = json.loads(content)
    validate_output(payload)

    usage = response.usage
    input_tokens = getattr(usage, "input_tokens", None) if usage else None
    output_tokens = getattr(usage, "output_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None

    metrics = ExtractionMetrics(
        model=model_name,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=_estimate_cost(input_tokens, output_tokens),
    )
    return ExtractionResult(payload=payload, metrics=metrics)


def extract_meeting(meeting: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible payload-only extraction helper."""
    return extract_meeting_with_metrics(meeting).payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract structured actions and decisions from meeting notes."
    )
    parser.add_argument("input", type=Path, help="Path to a meeting input JSON file.")
    parser.add_argument("--output", type=Path, help="Optional output JSON path. Defaults to stdout.")
    parser.add_argument(
        "--metrics-output",
        type=Path,
        help="Optional path for latency/token/cost metadata.",
    )
    parser.add_argument("--model", help="Optional model override. Otherwise HERMES_MODEL is used.")
    args = parser.parse_args()

    meeting = _read_json(args.input)
    result = extract_meeting_with_metrics(meeting, model=args.model)
    rendered = json.dumps(result.payload, indent=2, ensure_ascii=False) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    if args.metrics_output:
        args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_output.write_text(
            json.dumps(asdict(result.metrics), indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
