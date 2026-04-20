from __future__ import annotations

from typing import Any


REQUIRED_FAILURE_FIELDS = [
    "symptom",
    "trigger_condition",
    "root_cause",
    "failure_command",
]


def validate_failure_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            normalized[key] = value.strip()
        else:
            normalized[key] = ""

    missing_fields = [
        field for field in REQUIRED_FAILURE_FIELDS if not normalized.get(field, "")
    ]
    status = "pass" if not missing_fields else "fail"

    return {
        "status": status,
        "required_fields": REQUIRED_FAILURE_FIELDS,
        "missing_fields": missing_fields,
        "payload": payload,
    }
