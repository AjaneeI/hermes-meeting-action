from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable


TEXT_THRESHOLD = 0.78


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value.lower())).strip()


def _text_similarity(expected: str | None, actual: str | None) -> float:
    if expected is None and actual is None:
        return 1.0
    if expected is None or actual is None:
        return 0.0
    left = _normalize_text(expected)
    right = _normalize_text(actual)
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _scalar_equal(expected: Any, actual: Any) -> bool:
    if isinstance(expected, str) or isinstance(actual, str):
        return _normalize_text(expected) == _normalize_text(actual)
    return expected == actual


class Score:
    def __init__(self) -> None:
        self.earned = 0.0
        self.possible = 0.0
        self.checks: list[dict[str, Any]] = []

    def add(
        self,
        name: str,
        passed: bool,
        *,
        weight: float = 1.0,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.possible += weight
        if passed:
            self.earned += weight
        item = {"field": name, "passed": passed, "weight": weight}
        if detail:
            item.update(detail)
        self.checks.append(item)

    def as_dict(self) -> dict[str, Any]:
        value = self.earned / self.possible if self.possible else 1.0
        return {
            "score": round(value, 4),
            "earned": round(self.earned, 2),
            "possible": round(self.possible, 2),
            "failed_fields": [item["field"] for item in self.checks if not item["passed"]],
            "checks": self.checks,
        }


def _score_text(
    score: Score,
    name: str,
    expected: str | None,
    actual: str | None,
    threshold: float,
) -> None:
    similarity = _text_similarity(expected, actual)
    score.add(
        name,
        similarity >= threshold,
        detail={"similarity": round(similarity, 4), "expected": expected, "actual": actual},
    )


def _score_scalar(score: Score, name: str, expected: Any, actual: Any) -> None:
    score.add(name, _scalar_equal(expected, actual), detail={"expected": expected, "actual": actual})


def _best_text_matches(
    expected_values: Iterable[str | None],
    actual_values: Iterable[str | None],
) -> list[tuple[str | None, str | None, float]]:
    remaining = list(actual_values)
    pairs: list[tuple[str | None, str | None, float]] = []
    for expected in expected_values:
        if not remaining:
            pairs.append((expected, None, 0.0))
            continue
        scored = [
            (_text_similarity(expected, candidate), index, candidate)
            for index, candidate in enumerate(remaining)
        ]
        similarity, index, actual = max(scored, key=lambda item: item[0])
        pairs.append((expected, actual, similarity))
        remaining.pop(index)
    return pairs


def _score_evidence(
    score: Score,
    prefix: str,
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    threshold: float,
) -> None:
    score.add(
        f"{prefix}.count",
        len(expected) == len(actual),
        detail={"expected": len(expected), "actual": len(actual)},
    )
    remaining = list(actual)
    for index, expected_item in enumerate(expected):
        if not remaining:
            _score_text(score, f"{prefix}[{index}].quote", expected_item.get("quote"), None, threshold)
            _score_scalar(score, f"{prefix}[{index}].speaker", expected_item.get("speaker"), None)
            continue

        candidates = [
            (
                _text_similarity(expected_item.get("quote"), candidate.get("quote")),
                candidate_index,
                candidate,
            )
            for candidate_index, candidate in enumerate(remaining)
        ]
        similarity, candidate_index, actual_item = max(candidates, key=lambda item: item[0])
        remaining.pop(candidate_index)
        score.add(
            f"{prefix}[{index}].quote",
            similarity >= threshold,
            detail={
                "similarity": round(similarity, 4),
                "expected": expected_item.get("quote"),
                "actual": actual_item.get("quote"),
            },
        )
        _score_scalar(
            score,
            f"{prefix}[{index}].speaker",
            expected_item.get("speaker"),
            actual_item.get("speaker"),
        )


def _sort_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: str(item.get("id", "")))


def _score_decisions(
    score: Score,
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    threshold: float,
) -> None:
    score.add(
        "decisions.count",
        len(expected) == len(actual),
        detail={"expected": len(expected), "actual": len(actual)},
    )
    expected_sorted = _sort_by_id(expected)
    actual_sorted = _sort_by_id(actual)
    for index, expected_item in enumerate(expected_sorted):
        actual_item = actual_sorted[index] if index < len(actual_sorted) else {}
        _score_scalar(score, f"decisions[{index}].id", expected_item.get("id"), actual_item.get("id"))
        _score_text(
            score,
            f"decisions[{index}].statement",
            expected_item.get("statement"),
            actual_item.get("statement"),
            threshold,
        )
        _score_evidence(
            score,
            f"decisions[{index}].evidence",
            expected_item.get("evidence", []),
            actual_item.get("evidence", []),
            threshold,
        )


def _score_actions(
    score: Score,
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    threshold: float,
) -> None:
    score.add(
        "actions.count",
        len(expected) == len(actual),
        detail={"expected": len(expected), "actual": len(actual)},
    )
    expected_sorted = _sort_by_id(expected)
    actual_sorted = _sort_by_id(actual)
    for index, expected_item in enumerate(expected_sorted):
        actual_item = actual_sorted[index] if index < len(actual_sorted) else {}
        _score_scalar(score, f"actions[{index}].id", expected_item.get("id"), actual_item.get("id"))
        _score_text(score, f"actions[{index}].title", expected_item.get("title"), actual_item.get("title"), threshold)
        _score_text(
            score,
            f"actions[{index}].details",
            expected_item.get("details"),
            actual_item.get("details"),
            threshold,
        )

        expected_owner = expected_item.get("owner", {})
        actual_owner = actual_item.get("owner", {})
        _score_scalar(score, f"actions[{index}].owner.name", expected_owner.get("name"), actual_owner.get("name"))
        _score_scalar(score, f"actions[{index}].owner.status", expected_owner.get("status"), actual_owner.get("status"))

        expected_due = expected_item.get("due", {})
        actual_due = actual_item.get("due", {})
        _score_scalar(score, f"actions[{index}].due.date", expected_due.get("date"), actual_due.get("date"))
        _score_text(
            score,
            f"actions[{index}].due.date_text",
            expected_due.get("date_text"),
            actual_due.get("date_text"),
            threshold,
        )
        _score_scalar(score, f"actions[{index}].due.status", expected_due.get("status"), actual_due.get("status"))

        _score_evidence(
            score,
            f"actions[{index}].evidence",
            expected_item.get("evidence", []),
            actual_item.get("evidence", []),
            threshold,
        )
        _score_scalar(
            score,
            f"actions[{index}].ambiguity_flags",
            sorted(expected_item.get("ambiguity_flags", [])),
            sorted(actual_item.get("ambiguity_flags", [])),
        )
        _score_scalar(
            score,
            f"actions[{index}].approval_state",
            expected_item.get("approval_state"),
            actual_item.get("approval_state"),
        )


def _score_questions(
    score: Score,
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    threshold: float,
) -> None:
    score.add(
        "open_questions.count",
        len(expected) == len(actual),
        detail={"expected": len(expected), "actual": len(actual)},
    )
    expected_sorted = _sort_by_id(expected)
    actual_sorted = _sort_by_id(actual)
    for index, expected_item in enumerate(expected_sorted):
        actual_item = actual_sorted[index] if index < len(actual_sorted) else {}
        _score_scalar(score, f"open_questions[{index}].id", expected_item.get("id"), actual_item.get("id"))
        _score_text(
            score,
            f"open_questions[{index}].question",
            expected_item.get("question"),
            actual_item.get("question"),
            threshold,
        )
        _score_evidence(
            score,
            f"open_questions[{index}].evidence",
            expected_item.get("evidence", []),
            actual_item.get("evidence", []),
            threshold,
        )


def _score_review(
    score: Score,
    expected: dict[str, Any],
    actual: dict[str, Any],
    threshold: float,
) -> None:
    _score_scalar(
        score,
        "review.needs_human_review",
        expected.get("needs_human_review"),
        actual.get("needs_human_review"),
    )
    expected_reasons = expected.get("reasons", [])
    actual_reasons = actual.get("reasons", [])
    score.add(
        "review.reasons.count",
        len(expected_reasons) == len(actual_reasons),
        detail={"expected": len(expected_reasons), "actual": len(actual_reasons)},
    )
    for index, (expected_reason, actual_reason, similarity) in enumerate(
        _best_text_matches(expected_reasons, actual_reasons)
    ):
        score.add(
            f"review.reasons[{index}]",
            similarity >= threshold,
            detail={
                "similarity": round(similarity, 4),
                "expected": expected_reason,
                "actual": actual_reason,
            },
        )


def score_case(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    text_threshold: float = TEXT_THRESHOLD,
) -> dict[str, Any]:
    score = Score()

    _score_scalar(score, "schema_version", expected.get("schema_version"), actual.get("schema_version"))

    expected_meeting = expected.get("meeting", {})
    actual_meeting = actual.get("meeting", {})
    _score_scalar(score, "meeting.source_id", expected_meeting.get("source_id"), actual_meeting.get("source_id"))
    _score_text(score, "meeting.title", expected_meeting.get("title"), actual_meeting.get("title"), text_threshold)
    _score_scalar(score, "meeting.occurred_on", expected_meeting.get("occurred_on"), actual_meeting.get("occurred_on"))

    _score_decisions(score, expected.get("decisions", []), actual.get("decisions", []), text_threshold)
    _score_actions(score, expected.get("actions", []), actual.get("actions", []), text_threshold)
    _score_questions(score, expected.get("open_questions", []), actual.get("open_questions", []), text_threshold)
    _score_review(score, expected.get("review", {}), actual.get("review", {}), text_threshold)

    return score.as_dict()
