from __future__ import annotations

_KEYS = (
    "portrait", "lyrics", "style", "exclude", "emotion_focus", "persona_used",
    "selected_ids", "anchor_source_paths", "anchor_used", "anchor_song_name", "anchor_chorus_status",
    "review_skipped", "review_decision", "review_reason", "lyrics_changed", "polish_passes", "polish_diffs",
    "platform_adapt_status", "platform_adapt_raw_response",
    "llm_total_input_tokens", "llm_total_output_tokens", "llm_total_calls",
)
_LIST_KEYS = frozenset(())


def make_trace(out: dict) -> dict:
    return {k: (out.get(k) or []) if k in _LIST_KEYS else out.get(k) for k in _KEYS}
