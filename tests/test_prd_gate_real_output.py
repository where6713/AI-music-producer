"""PRD v1.3 gate tests: real assets + real output."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_real_cliche_dictionary_blocks_mingzhongzhuding() -> None:
    """Real local blacklist must block the cliche phrase 命中注定."""
    from src.producer_tools.business.lyric_architect import (
        _load_cliche_blacklist,
        check_anti_cliche,
    )

    blacklist = _load_cliche_blacklist(PROJECT_ROOT / "data" / "cliche_blacklist.json")
    assert "命中注定" in blacklist

    result = check_anti_cliche(["我们都说这是命中注定"], blacklist=blacklist)
    assert result["pass"] is False
    phrases = [v.get("phrase") for v in result.get("violations", [])]
    assert "命中注定" in phrases


def test_show_me_output_assembles_real_system_prompt() -> None:
    """Router must print a real, assembled prompt from local assets."""
    from src.producer_tools.business.lyric_architect import assemble_system_prompt_from_assets

    reference_dna = {
        "key": "C# minor",
        "tempo": 101,
        "energy_curve": [
            {"time": 0.0, "energy": 0.31},
            {"time": 12.0, "energy": 0.52},
            {"time": 28.0, "energy": 0.81},
        ],
        "instrumentation": {
            "vocals": {"presence": True},
            "drums": {"presence": True},
            "other": {"presence": True},
        },
    }

    result = assemble_system_prompt_from_assets(
        reference_dna=reference_dna,
        data_dir=PROJECT_ROOT / "data",
    )

    assert result["ok"] is True
    prompt = result["system_prompt"]
    assert isinstance(prompt, str)
    assert len(prompt) >= 1000
    assert "reference_dna" in prompt
    assert "命中注定" in prompt
    assert "开口音" in prompt

    # No placeholders / fake scaffolding allowed in final assembled text.
    assert "mock_data" not in prompt
    assert "Lorem ipsum" not in prompt
    assert "TODO_FILL" not in prompt
    assert "{" not in prompt
    assert "}" not in prompt


def test_open_vowel_rule_enforced_at_peak_position() -> None:
    """PRD gate: closed vowel at peak fails, open vowel at peak passes."""
    from src.producer_tools.business.lyric_architect import check_vowel_openness

    closed_case = check_vowel_openness(["你还在这里"], [0])  # "你" -> i
    assert closed_case["pass"] is False

    open_case = check_vowel_openness(["放开别躲"], [0])  # "放" -> ang
    assert open_case["pass"] is True
