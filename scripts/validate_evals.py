from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_meeting_action.validator import validate_output  # noqa: E402


def main() -> None:
    cases_path = ROOT / "evals" / "meeting_notes_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))

    failures: list[str] = []
    for case in cases:
        case_id = case.get("id", "<missing-id>")
        try:
            validate_output(case["expected_output"])
        except Exception as exc:  # surface exact schema failure for baseline debugging
            failures.append(f"{case_id}: {exc}")

    if failures:
        print("Expected-output schema validation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(f"Validated {len(cases)} expected outputs against schema v0.1.0.")


if __name__ == "__main__":
    main()
