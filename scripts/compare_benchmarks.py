from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _by_case(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["case_id"]: record for record in payload.get("cases", [])}


def _confidence_values(output: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for group in ("decisions", "actions", "open_questions"):
        for item in output.get(group, []):
            value = item.get("confidence")
            if isinstance(value, (int, float)):
                values.append(float(value))
    return values


def should_escalate(record: dict[str, Any], confidence_threshold: float) -> bool:
    if record.get("status") != "ok":
        return True

    output = record.get("actual_output", {})
    values = _confidence_values(output)
    if values and min(values) < confidence_threshold:
        return True

    review = output.get("review", {})
    reasons = " ".join(str(reason).lower() for reason in review.get("reasons", []))
    uncertainty_terms = ("conflict", "contradict", "low confidence", "uncertain evidence")
    return any(term in reasons for term in uncertainty_terms)


def _case_cost(record: dict[str, Any]) -> float | None:
    if record.get("status") != "ok":
        return None
    return record.get("metrics", {}).get("estimated_cost_usd")


def _case_latency(record: dict[str, Any]) -> float | None:
    if record.get("status") != "ok":
        return None
    return record.get("metrics", {}).get("latency_ms")


def compare_runs(
    low: dict[str, Any],
    strong: dict[str, Any],
    *,
    confidence_threshold: float,
) -> dict[str, Any]:
    low_cases = _by_case(low)
    strong_cases = _by_case(strong)
    common_ids = sorted(set(low_cases) & set(strong_cases))

    rows: list[dict[str, Any]] = []
    routed_scores: list[float] = []
    routed_costs: list[float] = []
    routed_latencies: list[float] = []

    for case_id in common_ids:
        low_record = low_cases[case_id]
        strong_record = strong_cases[case_id]
        escalate = should_escalate(low_record, confidence_threshold)

        chosen = strong_record if escalate and strong_record.get("status") == "ok" else low_record
        chosen_score = chosen.get("score", {}).get("score") if chosen.get("status") == "ok" else None
        if chosen_score is not None:
            routed_scores.append(chosen_score)

        low_cost = _case_cost(low_record)
        strong_cost = _case_cost(strong_record)
        route_cost = low_cost
        if escalate and strong_cost is not None:
            route_cost = (route_cost or 0.0) + strong_cost
        if route_cost is not None:
            routed_costs.append(route_cost)

        low_latency = _case_latency(low_record)
        strong_latency = _case_latency(strong_record)
        route_latency = low_latency
        if escalate and strong_latency is not None:
            route_latency = (route_latency or 0.0) + strong_latency
        if route_latency is not None:
            routed_latencies.append(route_latency)

        rows.append(
            {
                "case_id": case_id,
                "escalated": escalate,
                "low_score": low_record.get("score", {}).get("score"),
                "strong_score": strong_record.get("score", {}).get("score"),
                "routed_score": chosen_score,
                "low_cost_usd": low_cost,
                "strong_cost_usd": strong_cost,
                "routed_cost_usd": route_cost,
            }
        )

    return {
        "low_run": low.get("run", {}),
        "strong_run": strong.get("run", {}),
        "policy": {
            "confidence_threshold": confidence_threshold,
            "note": (
                "Escalate only on extraction errors, low object confidence, or review reasons "
                "that explicitly signal conflicting/uncertain evidence. Missing source facts alone "
                "do not trigger a stronger model."
            ),
        },
        "summary": {
            "cases_compared": len(common_ids),
            "cases_escalated": sum(1 for row in rows if row["escalated"]),
            "low_average_score": low.get("summary", {}).get("average_field_score"),
            "strong_average_score": strong.get("summary", {}).get("average_field_score"),
            "routed_average_score": round(mean(routed_scores), 4) if routed_scores else None,
            "low_total_cost_usd": low.get("summary", {}).get("estimated_cost_usd"),
            "strong_total_cost_usd": strong.get("summary", {}).get("estimated_cost_usd"),
            "routed_total_cost_usd": round(sum(routed_costs), 8)
            if routed_costs and len(routed_costs) == len(common_ids)
            else None,
            "routed_average_latency_ms": round(mean(routed_latencies), 2)
            if routed_latencies
            else None,
        },
        "cases": rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Hermes Model Comparison",
        "",
        f"- Cases compared: {summary['cases_compared']}",
        f"- Cases escalated by routing policy: {summary['cases_escalated']}",
        f"- Low-cost average field score: {summary['low_average_score']}",
        f"- Strong-model average field score: {summary['strong_average_score']}",
        f"- Routed average field score: {summary['routed_average_score']}",
        f"- Low-cost total estimated cost: {summary['low_total_cost_usd']}",
        f"- Strong-model total estimated cost: {summary['strong_total_cost_usd']}",
        f"- Routed total estimated cost: {summary['routed_total_cost_usd']}",
        "",
        "| Case | Escalated | Low score | Strong score | Routed score |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in payload["cases"]:
        lines.append(
            f"| {row['case_id']} | {'yes' if row['escalated'] else 'no'} | "
            f"{row['low_score']} | {row['strong_score']} | {row['routed_score']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare low-cost and stronger Hermes benchmark runs.")
    parser.add_argument("low_run", type=Path)
    parser.add_argument("strong_run", type=Path)
    parser.add_argument("--confidence-threshold", type=float, default=0.75)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    if not 0 <= args.confidence_threshold <= 1:
        parser.error("--confidence-threshold must be between 0 and 1.")

    payload = compare_runs(
        _load(args.low_run),
        _load(args.strong_run),
        confidence_threshold=args.confidence_threshold,
    )

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    markdown = _markdown(payload)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
