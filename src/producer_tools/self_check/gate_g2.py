from __future__ import annotations

from typing import Any


REQUIRED_FAILURE_FIELDS = [
    "symptom",
    "trigger_condition",
    "root_cause",
    "failure_command",
    "failure_output",
]


def validate_failure_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    missing_fields: list[str] = []
    for field in REQUIRED_FAILURE_FIELDS:
        value = payload.get(field, "")
        if not isinstance(value, str) or not value.strip():
            missing_fields.append(field)
    return {
        "status": "pass" if not missing_fields else "fail",
        "missing_fields": missing_fields,
        "required_fields": REQUIRED_FAILURE_FIELDS,
    }
