from __future__ import annotations

from typing import Any


REQUIRED_PASS_FIELDS = [
    "local_command",
    "local_result",
    "ci_result",
    "ci_run_url",
    "reproducible_commands",
]


def _normalize_result(value: str) -> str:
    token = value.strip().lower()
    if token in {"pass", "passed", "success", "ok", "green"}:
        return "pass"
    if token in {"fail", "failed", "error", "red"}:
        return "fail"
    return token


def validate_pass_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    missing_fields: list[str] = []

    for field in REQUIRED_PASS_FIELDS:
        if field not in payload:
            missing_fields.append(field)

    local_command = str(payload.get("local_command", "")).strip()
    local_result = str(payload.get("local_result", "")).strip()
    ci_result = str(payload.get("ci_result", "")).strip()
    ci_run_url = str(payload.get("ci_run_url", "")).strip()
    reproducible_commands_raw = payload.get("reproducible_commands", [])

    if not local_command and "local_command" not in missing_fields:
        missing_fields.append("local_command")
    if not local_result and "local_result" not in missing_fields:
        missing_fields.append("local_result")
    if not ci_result and "ci_result" not in missing_fields:
        missing_fields.append("ci_result")
    if not ci_run_url and "ci_run_url" not in missing_fields:
        missing_fields.append("ci_run_url")

    reproducible_commands: list[str] = []
    if isinstance(reproducible_commands_raw, list):
        reproducible_commands = [
            str(x).strip()
            for x in reproducible_commands_raw
            if isinstance(x, str) and str(x).strip()
        ]
    if not reproducible_commands and "reproducible_commands" not in missing_fields:
        missing_fields.append("reproducible_commands")

    local_status = _normalize_result(local_result)
    ci_status = _normalize_result(ci_result)
    consistent = bool(local_status and ci_status and local_status == ci_status)

    status = "pass"
    if missing_fields:
        status = "fail"
    elif not consistent:
        status = "fail"

    warnings: list[str] = []
    if status == "fail" and not missing_fields and not consistent:
        warnings.append("local_result and ci_result are inconsistent")

    return {
        "status": status,
        "required_fields": REQUIRED_PASS_FIELDS,
        "missing_fields": missing_fields,
        "local_status": local_status,
        "ci_status": ci_status,
        "consistent": consistent,
        "warnings": warnings,
        "payload": payload,
    }
