from __future__ import annotations

from src.lint import lint_payload
from src.schemas import LyricPayload


def _payload(hook_line: str, forbidden: list[str], chorus_tag: str = "[Chorus]") -> LyricPayload:
    data = {
        "distillation": {
            "emotional_register": "restrained",
            "core_tension": "conflict",
            "valence": "negative",
            "arousal": "medium",
            "forbidden_literal_phrases": forbidden,
        },
        "structure": {
            "section_order": ["[Verse 1]", chorus_tag],
            "hook_section": chorus_tag,
            "hook_line_index": 1,
        },
        "lyrics_by_section": [
            {
                "tag": "[Verse 1]",
                "voice_tags_inline": [],
                "lines": [
                    {"primary": "窗上水痕在退", "backing": "", "tail_pinyin": "tui4", "char_count": 7}
                ],
            },
            {
                "tag": chorus_tag,
                "voice_tags_inline": [],
                "lines": [
                    {"primary": hook_line, "backing": "", "tail_pinyin": "", "char_count": len(hook_line)}
                ],
            },
        ],
        "style_tags": {
            "genre": ["lo-fi r&b"],
            "mood": ["melancholic"],
            "instruments": ["soft keys"],
            "vocals": ["intimate male vocals"],
            "production": ["lo-fi warmth"],
        },
        "exclude_tags": ["EDM"],
    }
    return LyricPayload.model_validate(data)


def test_lint_passes_minimal_payload() -> None:
    payload = _payload("再把手放开", forbidden=["失恋三个月"])
    report = lint_payload(payload)
    assert report["pass"] is True


def test_lint_blocks_forbidden_literal_phrase() -> None:
    payload = _payload("我失恋三个月还在等你吧", forbidden=["失恋三个月"])
    report = lint_payload(payload)
    assert report["pass"] is False
    assert "R03" in report["failed_rules"]


def test_lint_blocks_invalid_tag() -> None:
    payload = _payload("把号码放下吧", forbidden=[], chorus_tag="[My Special Section]")
    report = lint_payload(payload)
    assert report["pass"] is False
    assert "R06" in report["failed_rules"]
