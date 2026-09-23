from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [record for record in records if record["status"] == "ok"]
    scored = [record["score"]["score"] for record in successful]
    latencies = [
        record["metrics"]["latency_ms"]
        for record in successful
        if record.get("metrics", {}).get("latency_ms") is not None
    ]
    costs = [
        record["metrics"]["estimated_cost_usd"]
        for record in successful
        if record.get("metrics", {}).get("estimated_cost_usd") is not None
    ]

    failed_field_counts: Counter[str] = Counter()
    semantic_mismatch_cases: list[dict[str, Any]] = []
    for record in successful:
        failed_fields = record.get("score", {}).get("failed_fields", [])
        failed_field_counts.update(failed_fields)
        if failed_fields:
            semantic_mismatch_cases.append(
                {
                    "case_id": record["case_id"],
                    "score": record["score"]["score"],
                    "failed_fields": failed_fields,
                }
            )

    return {
        "cases_total": len(records),
        "cases_succeeded": len(successful),
        "cases_failed": len(records) - len(successful),
        "cases_with_semantic_mismatches": len(semantic_mismatch_cases),
        "semantic_mismatch_cases": semantic_mismatch_cases,
        "failed_field_counts": dict(sorted(failed_field_counts.items())),
        "average_field_score": round(mean(scored), 4) if scored else None,
        "min_field_score": round(min(scored), 4) if scored else None,
        "perfect_cases": sum(1 for value in scored if value == 1.0),
        "average_latency_ms": round(mean(latencies), 2) if latencies else None,
        "total_input_tokens": sum(record["metrics"].get("input_tokens") or 0 for record in successful),
        "total_output_tokens": sum(record["metrics"].get("output_tokens") or 0 for record in successful),
        "total_tokens": sum(record["metrics"].get("total_tokens") or 0 for record in successful),
        "estimated_cost_usd": round(sum(costs), 8)
        if costs and len(costs) == len(successful)
        else None,
    }
