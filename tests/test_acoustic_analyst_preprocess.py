from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


acoustic_analyst = importlib.import_module("producer_tools.business.acoustic_analyst")


def test_missing_audio_path_returns_error() -> None:
    result = acoustic_analyst.run({"audio_path": "missing.wav"})

    assert result["ok"] is False
    assert result["error"] == "audio_not_found"
    assert Path(result["input_path"]).is_absolute()


def test_demucs_unavailable_falls_back_to_input(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.wav"
    sample_path.write_bytes(b"fake")

    def _demucs_unavailable() -> bool:
        return False

    original = acoustic_analyst._is_demucs_available
    setattr(acoustic_analyst, "_is_demucs_available", _demucs_unavailable)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_demucs": True,
                "is_vocal": False,
            }
        )
    finally:
        setattr(acoustic_analyst, "_is_demucs_available", original)

    assert result["ok"] is True
    assert result["preprocessed_path"] == str(sample_path.resolve())
    assert result["demucs"]["requested"] is True
    assert result["demucs"]["available"] is False
    assert result["demucs"]["ran"] is False
    assert result["demucs"]["reason"] == "demucs_unavailable"


def test_vocal_input_skips_demucs_even_if_requested(tmp_path: Path) -> None:
    sample_path = tmp_path / "vocal.wav"
    sample_path.write_bytes(b"fake")

    def _should_not_call() -> bool:
        raise AssertionError("demucs availability should not be checked")

    original = acoustic_analyst._is_demucs_available
    setattr(acoustic_analyst, "_is_demucs_available", _should_not_call)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_demucs": True,
                "is_vocal": True,
            }
        )
    finally:
        setattr(acoustic_analyst, "_is_demucs_available", original)

    assert result["ok"] is True
    assert result["preprocessed_path"] == str(sample_path.resolve())
    assert result["demucs"]["requested"] is True
    assert result["demucs"]["ran"] is False
    assert result["demucs"]["reason"] == "input_is_vocal"


def test_parselmouth_unavailable_falls_back_without_error(tmp_path: Path) -> None:
    sample_path = tmp_path / "voice.wav"
    sample_path.write_bytes(b"fake")

    def _parselmouth_unavailable() -> bool:
        return False

    original = acoustic_analyst._is_parselmouth_available
    setattr(acoustic_analyst, "_is_parselmouth_available", _parselmouth_unavailable)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_parselmouth": True,
            }
        )
    finally:
        setattr(acoustic_analyst, "_is_parselmouth_available", original)

    assert result["ok"] is True
    assert result["parselmouth"]["requested"] is True
    assert result["parselmouth"]["available"] is False
    assert result["parselmouth"]["ran"] is False
    assert result["parselmouth"]["reason"] == "parselmouth_unavailable"


def test_parselmouth_feature_extraction_records_metrics(tmp_path: Path) -> None:
    sample_path = tmp_path / "voice.wav"
    sample_path.write_bytes(b"fake")

    def _parselmouth_available() -> bool:
        return True

    def _extract_features(path: Path) -> dict[str, object]:
        assert path == sample_path.resolve()
        return {
            "f0": {"median": 180.0, "p10": 150.0, "p90": 220.0},
            "formants": {"f1": 500.0, "f2": 1600.0, "f3": 2500.0},
            "timbre": {"hnr": 12.5, "jitter": 0.01, "shimmer": 0.02},
            "dynamics": {"intensity_range": 15.0},
        }

    original_available = acoustic_analyst._is_parselmouth_available
    original_extract = acoustic_analyst._extract_parselmouth_features
    setattr(acoustic_analyst, "_is_parselmouth_available", _parselmouth_available)
    setattr(acoustic_analyst, "_extract_parselmouth_features", _extract_features)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_parselmouth": True,
            }
        )
    finally:
        setattr(acoustic_analyst, "_is_parselmouth_available", original_available)
        setattr(acoustic_analyst, "_extract_parselmouth_features", original_extract)

    assert result["ok"] is True
    assert result["parselmouth"]["requested"] is True
    assert result["parselmouth"]["available"] is True
    assert result["parselmouth"]["ran"] is True
    assert result["parselmouth"]["reason"] == "parselmouth_ran"
    assert result["parselmouth"]["features"]["f0"]["median"] == 180.0


def test_librosa_unavailable_marks_mfcc_as_unavailable(tmp_path: Path) -> None:
    sample_path = tmp_path / "voice.wav"
    sample_path.write_bytes(b"fake")

    def _librosa_unavailable() -> bool:
        return False

    original = acoustic_analyst._is_librosa_available
    setattr(acoustic_analyst, "_is_librosa_available", _librosa_unavailable)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_librosa": True,
            }
        )
    finally:
        setattr(acoustic_analyst, "_is_librosa_available", original)

    assert result["ok"] is True
    assert result["mfcc"]["requested"] is True
    assert result["mfcc"]["available"] is False
    assert result["mfcc"]["ran"] is False
    assert result["mfcc"]["reason"] == "librosa_unavailable"


def test_mfcc_and_clap_feature_extraction_records_vectors(tmp_path: Path) -> None:
    sample_path = tmp_path / "voice.wav"
    sample_path.write_bytes(b"fake")

    def _librosa_available() -> bool:
        return True

    def _clap_available() -> bool:
        return True

    def _extract_mfcc(path: Path, n_mfcc: int) -> dict[str, object]:
        assert path == sample_path.resolve()
        assert n_mfcc == 13
        return {
            "n_mfcc": n_mfcc,
            "frames": 2,
            "mean": [0.1, 0.2, 0.3],
        }

    def _extract_clap(path: Path) -> list[float]:
        assert path == sample_path.resolve()
        return [0.01, 0.02, 0.03, 0.04]

    original_librosa_available = acoustic_analyst._is_librosa_available
    original_clap_available = acoustic_analyst._is_clap_available
    original_extract_mfcc = acoustic_analyst._extract_mfcc_features
    original_extract_clap = acoustic_analyst._extract_clap_embedding
    setattr(acoustic_analyst, "_is_librosa_available", _librosa_available)
    setattr(acoustic_analyst, "_is_clap_available", _clap_available)
    setattr(acoustic_analyst, "_extract_mfcc_features", _extract_mfcc)
    setattr(acoustic_analyst, "_extract_clap_embedding", _extract_clap)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_librosa": True,
                "use_clap": True,
                "mfcc_n": 13,
            }
        )
    finally:
        setattr(acoustic_analyst, "_is_librosa_available", original_librosa_available)
        setattr(acoustic_analyst, "_is_clap_available", original_clap_available)
        setattr(acoustic_analyst, "_extract_mfcc_features", original_extract_mfcc)
        setattr(acoustic_analyst, "_extract_clap_embedding", original_extract_clap)

    assert result["ok"] is True
    assert result["mfcc"]["requested"] is True
    assert result["mfcc"]["ran"] is True
    assert result["mfcc"]["features"]["mean"][1] == 0.2
    assert result["clap"]["requested"] is True
    assert result["clap"]["ran"] is True
    assert result["clap"]["embedding"][2] == 0.03


def test_voice_profile_schema_output_and_write(tmp_path: Path) -> None:
    sample_path = tmp_path / "voice.wav"
    sample_path.write_bytes(b"fake")
    profile_path = tmp_path / "voice_profile.json"

    def _parselmouth_available() -> bool:
        return True

    def _librosa_available() -> bool:
        return True

    def _clap_available() -> bool:
        return True

    def _extract_parselmouth(_: Path) -> dict[str, object]:
        return {
            "f0": {
                "median": 185.0,
                "p10": 150.0,
                "p90": 230.0,
                "comfort_range": [160.0, 210.0],
                "absolute_high": 255.0,
            },
            "formants": {
                "f1": 510.0,
                "f2": 1650.0,
                "f3": 2600.0,
                "vowel_space_area": 1.2,
                "brightness": 0.8,
            },
            "timbre": {
                "hnr": 14.2,
                "jitter": 0.01,
                "shimmer": 0.02,
                "breathiness": 0.3,
                "roughness": 0.2,
            },
            "dynamics": {
                "intensity_range": 17.0,
                "phrase_length": 3.2,
            },
        }

    def _extract_mfcc(_: Path, __: int) -> dict[str, object]:
        return {"n_mfcc": 13, "frames": 2, "mean": [0.1, 0.2]}

    def _extract_clap(_: Path) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]

    original_parselmouth_available = acoustic_analyst._is_parselmouth_available
    original_librosa_available = acoustic_analyst._is_librosa_available
    original_clap_available = acoustic_analyst._is_clap_available
    original_extract_parselmouth = acoustic_analyst._extract_parselmouth_features
    original_extract_mfcc = acoustic_analyst._extract_mfcc_features
    original_extract_clap = acoustic_analyst._extract_clap_embedding
    setattr(acoustic_analyst, "_is_parselmouth_available", _parselmouth_available)
    setattr(acoustic_analyst, "_is_librosa_available", _librosa_available)
    setattr(acoustic_analyst, "_is_clap_available", _clap_available)
    setattr(acoustic_analyst, "_extract_parselmouth_features", _extract_parselmouth)
    setattr(acoustic_analyst, "_extract_mfcc_features", _extract_mfcc)
    setattr(acoustic_analyst, "_extract_clap_embedding", _extract_clap)
    try:
        result = acoustic_analyst.run(
            {
                "audio_path": str(sample_path),
                "use_parselmouth": True,
                "use_librosa": True,
                "use_clap": True,
                "voice_profile_path": str(profile_path),
            }
        )
    finally:
        setattr(
            acoustic_analyst,
            "_is_parselmouth_available",
            original_parselmouth_available,
        )
        setattr(acoustic_analyst, "_is_librosa_available", original_librosa_available)
        setattr(acoustic_analyst, "_is_clap_available", original_clap_available)
        setattr(
            acoustic_analyst,
            "_extract_parselmouth_features",
            original_extract_parselmouth,
        )
        setattr(acoustic_analyst, "_extract_mfcc_features", original_extract_mfcc)
        setattr(acoustic_analyst, "_extract_clap_embedding", original_extract_clap)

    assert result["ok"] is True
    assert result["voice_profile"]["f0"]["median"] == 185.0
    assert result["voice_profile"]["formants"]["f2"] == 1650.0
    assert result["voice_profile"]["timbre"]["hnr"] == 14.2
    assert result["voice_profile"]["dynamics"]["phrase_length"] == 3.2
    assert result["voice_profile"]["embedding_clap"][3] == 0.4
    assert Path(result["voice_profile_path"]) == profile_path.resolve()
    assert profile_path.exists()

    persisted = json.loads(profile_path.read_text(encoding="utf-8"))
    assert persisted["f0"]["absolute_high"] == 255.0
