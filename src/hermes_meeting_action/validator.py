from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "meeting_action_output.schema.json"


def load_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_output(payload: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA_PATH) -> None:
    """Raise jsonschema.ValidationError when an extraction violates the contract."""
    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(payload)
