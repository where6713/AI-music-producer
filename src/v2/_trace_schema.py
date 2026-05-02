from __future__ import annotations

_KEYS = (
    "portrait", "brief", "lyrics", "style", "exclude",
    "selected_ids", "anchor_source_paths", "anchor_used", "review_skipped",
    "llm_total_input_tokens", "llm_total_output_tokens", "llm_total_calls",
)
_LIST_KEYS = frozenset(())


def make_trace(out: dict) -> dict:
    return {k: (out.get(k) or []) if k in _LIST_KEYS else out.get(k) for k in _KEYS}
