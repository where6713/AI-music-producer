from __future__ import annotations

from collections.abc import Mapping


def translate_result(
    action: str,
    status: str,
    context: Mapping[str, object] | None = None,
) -> str:
    payload: Mapping[str, object] = context or {}
    templates: dict[tuple[str, str], str] = {
        ("status_ready", "ok"): "AI music producer ready",
        (
            "plan_required",
            "error",
        ): "Plan required for long-running actions. Provide plan and plan-step.",
        ("plan_missing", "error"): "Plan file not found: {plan_path}",
        (
            "checkpoint_required",
            "error",
        ): "Checkpoint path is required for --checkpoint",
        (
            "checkpoint_missing",
            "error",
        ): "Checkpoint not found: {checkpoint_path}",
        ("resume", "ok"): "Resuming from checkpoint (step={step})",
        (
            "plan_acknowledged",
            "ok",
        ): "Plan acknowledged ({plan_step}). Starting production...",
        (
            "production_completed",
            "ok",
        ): "Production completed. Checkpoint saved: {checkpoint_path}",
        ("context_empty", "ok"): "No project memory context available.",
    }

    template = templates.get((action, status))
    if template is None:
        return f"Action {action} returned status {status}."
    try:
        return template.format(**payload)
    except KeyError:
        return template
