from __future__ import annotations

from typing import Any


REQUIRED_PASS_FIELDS = [
    "local_command",
    "local_result",
    "ci_result",
    "ci_run_url",
    "reproducible_commands",
]


def _normalize(value: str) -> str:
    token = value.strip().lower()
    if token in {"pass", "passed", "success", "ok", "green"}:
        return "pass"
    if token in {"fail", "failed", "error", "red"}:
        return "fail"
    return token


def validate_pass_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    missing_fields: list[str] = []
    for field in REQUIRED_PASS_FIELDS:
        value = payload.get(field)
        if field == "reproducible_commands":
            if not isinstance(value, list) or not [x for x in value if isinstance(x, str) and x.strip()]:
                missing_fields.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing_fields.append(field)

    local = _normalize(str(payload.get("local_result", "")))
    ci = _normalize(str(payload.get("ci_result", "")))
    consistent = bool(local and ci and local == ci)

    warnings: list[str] = []
    if not missing_fields and not consistent:
        warnings.append("local_result and ci_result are inconsistent")

    return {
        "status": "pass" if (not missing_fields and consistent) else "fail",
        "missing_fields": missing_fields,
        "required_fields": REQUIRED_PASS_FIELDS,
        "consistent": consistent,
        "warnings": warnings,
    }
