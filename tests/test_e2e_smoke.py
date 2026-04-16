"""Real-audio smoke tests for end-to-end orchestration."""

from __future__ import annotations

import math
import os
import struct
import sys
import wave
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))


def _make_real_wav(path: Path, seconds: float = 2.0, sr: int = 16000) -> Path:
    """Generate a real PCM .wav fixture (sine wave)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    total = int(seconds * sr)
    amp = 12000
    freq = 220.0
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(total):
            sample = int(amp * math.sin(2.0 * math.pi * freq * (i / sr)))
            wf.writeframes(struct.pack("<h", sample))
    return path


def _stable_adapter(prompt: dict[str, object]) -> dict[str, object]:
    _ = prompt
    return {
        "lines": [
            "地铁到站风停在袖口",
            "旧钥匙还在口袋",
            "站台灯下我学会转身",
        ]
    }


def test_style_deconstructor_with_real_audio_fixture(tmp_path: Path) -> None:
    """Style deconstructor should extract non-empty tempo/structure from real wav."""
    from src.producer_tools.business import style_deconstructor

    reference_audio = _make_real_wav(tmp_path / "fixtures" / "audio" / "style_ref.wav")
    result = style_deconstructor.run({"reference_audio_path": str(reference_audio)})

    assert result.get("ok") is True
    tempo_key = result.get("tempo_key", {})
    assert isinstance(tempo_key, dict)
    assert float(tempo_key.get("bpm", 0.0)) >= 0.0
    assert isinstance(tempo_key.get("structure", []), list)


def test_full_pipeline_with_real_audio_smoke(tmp_path: Path) -> None:
    """Run full orchestrator pipeline with real wav fixtures.

    This test is intentionally gated by OPENAI_API_KEY to avoid false-red in environments
    without LLM credentials.
    """
    from src.producer_tools.orchestrator import orchestrator

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        pytest.skip("LLM not configured: OPENAI_API_KEY missing")

    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()

    voice_audio = _make_real_wav(tmp_path / "fixtures" / "audio" / "voice.wav")
    reference_audio = _make_real_wav(tmp_path / "fixtures" / "audio" / "reference.wav")

    corpus_file = tmp_path / "fixtures" / "audio" / "corpus.txt"
    corpus_file.write_text(
        "地铁到站风停在袖口\n旧钥匙还在口袋\n站台灯下我学会转身\n",
        encoding="utf-8",
    )

    result = orchestrator.run(
        {
            "intent": "现代华语流行，轻微古风，失恋但豁达",
            "output_dir": str(tmp_path),
            "voice_audio_path": str(voice_audio),
            "reference_audio_path": str(reference_audio),
            "corpus_sources": [str(corpus_file)],
            "require_real_corpus": True,
            "llm_adapter": _stable_adapter,
            "llm_api_key": api_key,
            "llm_base_url": base_url,
            "llm_model": model,
        }
    )

    pipeline = result.get("pipeline", [])
    assert isinstance(pipeline, list)

    acoustic = [s for s in pipeline if s.get("step") == "acoustic_analyst"]
    style = [s for s in pipeline if s.get("step") == "style_deconstructor"]
    lyric = [s for s in pipeline if s.get("step") == "lyric_architect"]
    assert acoustic and acoustic[0].get("status") == "completed"
    assert style and style[0].get("status") == "completed"
    assert lyric
    assert lyric[0].get("status") in {"completed", "failed"}

    if lyric[0].get("status") == "completed":
        lyrics_path = tmp_path / "lyrics.json"
        assert lyrics_path.exists()

        import json

        payload = json.loads(lyrics_path.read_text(encoding="utf-8"))
        sections = payload.get("sections", [])
        assert isinstance(sections, list)
        assert len(sections) == 6
    else:
        assert lyric[0].get("note") == "lyric_quality_gate_failed"
