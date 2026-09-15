from __future__ import annotations

import json
from pathlib import Path

from hermes_meeting_action.scoring import score_case


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "meeting_notes_cases.json"


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    failed: list[str] = []
    for case in cases:
        result = score_case(case["expected_output"], case["expected_output"])
        if result["score"] != 1.0:
            failed.append(f"{case['id']}: {result['score']}")
    if failed:
        raise SystemExit("Reference scorer smoke test failed:\n" + "\n".join(failed))
    print(f"Scorer smoke test passed for {len(cases)} reference cases.")


if __name__ == "__main__":
    main()
