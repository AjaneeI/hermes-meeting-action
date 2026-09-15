from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from .validator import validate_output


ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "extraction_system.txt"
SCHEMA_PATH = ROOT / "schemas" / "meeting_action_output.schema.json"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def extract_meeting(meeting: dict[str, Any]) -> dict[str, Any]:
    model = os.environ.get("HERMES_MODEL")
    if not model:
        raise RuntimeError("Set HERMES_MODEL to the model identifier to use.")

    api_key = os.environ.get("HERMES_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set HERMES_API_KEY or OPENAI_API_KEY.")

    base_url = os.environ.get("HERMES_BASE_URL")
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    schema = _read_json(SCHEMA_PATH)
    system_prompt = _read_text(SYSTEM_PROMPT_PATH)

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(meeting)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "hermes_meeting_action_output",
                "strict": True,
                "schema": schema,
            },
        },
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Model returned an empty response.")

    payload = json.loads(content)
    validate_output(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured actions and decisions from meeting notes.")
    parser.add_argument("input", type=Path, help="Path to a meeting input JSON file.")
    parser.add_argument("--output", type=Path, help="Optional output JSON path. Defaults to stdout.")
    args = parser.parse_args()

    meeting = _read_json(args.input)
    payload = extract_meeting(meeting)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
