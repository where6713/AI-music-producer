from __future__ import annotations

import importlib
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


style_deconstructor = importlib.import_module(
    "producer_tools.business.style_deconstructor"
)


def test_missing_reference_audio_returns_error() -> None:
    result = style_deconstructor.run({"reference_audio_path": "missing.wav"})

    assert result["ok"] is False
    assert result["error"] == "reference_audio_not_found"
    assert Path(result["input_path"]).is_absolute()


def test_demucs_unavailable_fails_fast(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    def _demucs_unavailable() -> bool:
        return False

    original = style_deconstructor._is_demucs_available
    setattr(style_deconstructor, "_is_demucs_available", _demucs_unavailable)
    try:
        result = style_deconstructor.run(
            {
                "reference_audio_path": str(reference_path),
                "use_demucs": True,
            }
        )
    finally:
        setattr(style_deconstructor, "_is_demucs_available", original)

    assert result["ok"] is False
    assert result["error"] == "demucs_unavailable"
    assert result["demucs"]["requested"] is True
    assert result["demucs"]["available"] is False
    assert result["demucs"]["reason"] == "demucs_unavailable"
    assert result["stems"] == {}


def test_demucs_decomposition_returns_six_stems(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    stems = {
        "vocals": str((tmp_path / "vocals.wav").resolve()),
        "drums": str((tmp_path / "drums.wav").resolve()),
        "bass": str((tmp_path / "bass.wav").resolve()),
        "guitar": str((tmp_path / "guitar.wav").resolve()),
        "piano": str((tmp_path / "piano.wav").resolve()),
        "other": str((tmp_path / "other.wav").resolve()),
    }

    def _demucs_available() -> bool:
        return True

    def _run_demucs(path: Path, output_dir: Path, model: str) -> dict[str, str]:
        assert path == reference_path.resolve()
        assert model == "htdemucs_6s"
        assert output_dir.exists()
        return stems

    original_available = style_deconstructor._is_demucs_available
    original_run = style_deconstructor._run_demucs_6s
    setattr(style_deconstructor, "_is_demucs_available", _demucs_available)
    setattr(style_deconstructor, "_run_demucs_6s", _run_demucs)
    try:
        result = style_deconstructor.run(
            {
                "reference_audio_path": str(reference_path),
                "use_demucs": True,
                "demucs_model": "htdemucs_6s",
            }
        )
    finally:
        setattr(style_deconstructor, "_is_demucs_available", original_available)
        setattr(style_deconstructor, "_run_demucs_6s", original_run)

    assert result["ok"] is True
    assert result["demucs"]["ran"] is True
    assert result["demucs"]["reason"] == "demucs_ran"
    assert result["stems"] == stems
