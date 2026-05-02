from __future__ import annotations

_KEYS = (
    "portrait", "motive", "hook_seed", "selected_ids", "anchor_source_paths",
    "quality_gate_failed", "selection_mode", "review_notes",
    "recalled_pool_size", "golden_refs_used", "pass1_selected_ids_count",
    "retry_count", "llm_total_calls", "llm_total_input_tokens", "llm_total_output_tokens",
    "retry_modes", "failure_reasons",
)
_LIST_KEYS = frozenset(("retry_modes", "failure_reasons"))


def make_trace(out: dict) -> dict:
    return {k: (out.get(k) or []) if k in _LIST_KEYS else out.get(k) for k in _KEYS}
