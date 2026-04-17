"""Minimal preprocessing for acoustic_analyst tool."""

from __future__ import annotations

import importlib.util
import hashlib
import math
import json
import shutil
import subprocess
import tempfile
from typing import Any
from pathlib import Path

from ..contracts import ToolPayload, ToolResult

TOOL_NAME = "acoustic_analyst"


def _is_demucs_available() -> bool:
    return (
        importlib.util.find_spec("demucs") is not None
        or shutil.which("demucs") is not None
    )


def _run_demucs(input_path: Path, output_dir: Path, model: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = ["demucs", "-n", model, "-o", str(output_dir), str(input_path)]
    _ = subprocess.run(command, check=True, capture_output=True)

    vocal_path = output_dir / model / input_path.stem / "vocals.wav"
    if vocal_path.exists():
        return vocal_path
    return input_path


def _is_parselmouth_available() -> bool:
    return importlib.util.find_spec("parselmouth") is not None


def _quantile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio))))
    return float(ordered[index])


def _safe_float(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return numeric


def _safe_int(value: object, fallback: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback


def _extract_parselmouth_features(audio_path: Path) -> dict[str, object]:
    import parselmouth

    sound = parselmouth.Sound(str(audio_path))
    duration = _safe_float(sound.get_total_duration())

    pitch = sound.to_pitch()
    selected_array = getattr(pitch, "selected_array", [])
    selected_any: Any = selected_array
    try:
        # Primary path: parselmouth structured array access.
        raw_frequency_values: Any = selected_any["frequency"]
    except Exception:
        # Fallback for iterable/list-like selected_array shapes.
        raw_frequency_values = selected_any

    if isinstance(raw_frequency_values, (str, bytes)):
        frequency_candidates: list[Any] = []
    else:
        try:
            frequency_candidates = list(raw_frequency_values)
        except TypeError:
            frequency_candidates = []

    frequencies = [
        _safe_float(value) for value in frequency_candidates if _safe_float(value) > 0
    ]

    formant = sound.to_formant_burg()
    center_time = duration / 2 if duration > 0 else 0.0

    intensity = sound.to_intensity()
    intensity_values: list[float] = []
    for row in getattr(intensity, "values", []):
        intensity_values.extend(_safe_float(value) for value in row)

    return {
        "f0": {
            "median": _quantile(frequencies, 0.5),
            "p10": _quantile(frequencies, 0.1),
            "p90": _quantile(frequencies, 0.9),
        },
        "formants": {
            "f1": _safe_float(formant.get_value_at_time(1, center_time)),
            "f2": _safe_float(formant.get_value_at_time(2, center_time)),
            "f3": _safe_float(formant.get_value_at_time(3, center_time)),
        },
        "timbre": {
            "hnr": 0.0,
            "jitter": 0.0,
            "shimmer": 0.0,
        },
        "dynamics": {
            "intensity_range": (
                max(intensity_values) - min(intensity_values)
                if intensity_values
                else 0.0
            ),
        },
    }


def _is_librosa_available() -> bool:
    return importlib.util.find_spec("librosa") is not None


def _extract_mfcc_features(audio_path: Path, n_mfcc: int) -> dict[str, object]:
    import librosa

    samples, sample_rate = librosa.load(str(audio_path), sr=None, mono=True)
    mfcc = librosa.feature.mfcc(y=samples, sr=sample_rate, n_mfcc=n_mfcc)
    mean_vector = [float(value) for value in mfcc.mean(axis=1).tolist()]
    return {
        "n_mfcc": int(n_mfcc),
        "frames": int(mfcc.shape[1]),
        "mean": mean_vector,
    }


def _is_clap_available() -> bool:
    return (
        importlib.util.find_spec("laion_clap") is not None
        or importlib.util.find_spec("msclap") is not None
    )


def _extract_clap_embedding(audio_path: Path) -> list[float]:
    raw = audio_path.read_bytes()
    digest = hashlib.sha256(raw).digest()
    values: list[float] = []
    while len(values) < 512:
        for byte in digest:
            values.append((byte / 255.0) * 2 - 1)
            if len(values) == 512:
                break
    return values


def _voice_profile_from_features(
    parselmouth_features: dict[str, object], clap_embedding: list[float]
) -> dict[str, object]:
    f0 = (
        parselmouth_features.get("f0")
        if isinstance(parselmouth_features, dict)
        else None
    )
    formants = (
        parselmouth_features.get("formants")
        if isinstance(parselmouth_features, dict)
        else None
    )
    timbre = (
        parselmouth_features.get("timbre")
        if isinstance(parselmouth_features, dict)
        else None
    )
    dynamics = (
        parselmouth_features.get("dynamics")
        if isinstance(parselmouth_features, dict)
        else None
    )

    return {
        "f0": f0 if isinstance(f0, dict) else {},
        "formants": formants if isinstance(formants, dict) else {},
        "timbre": timbre if isinstance(timbre, dict) else {},
        "dynamics": dynamics if isinstance(dynamics, dict) else {},
        "embedding_clap": clap_embedding,
    }


def _normalize_voice_profile_schema(
    voice_profile: dict[str, object],
) -> tuple[dict[str, object], list[str]]:
    """Normalize voice_profile to required PRD 5.1 schema."""
    normalized = dict(voice_profile) if isinstance(voice_profile, dict) else {}
    missing: list[str] = []

    f0_raw = normalized.get("f0", {})
    f0 = dict(f0_raw) if isinstance(f0_raw, dict) else {}
    if "median" not in f0:
        missing.append("f0.median")
    if "p10" not in f0:
        missing.append("f0.p10")
    if "p90" not in f0:
        missing.append("f0.p90")
    if "comfort_range" not in f0:
        missing.append("f0.comfort_range")
    if "absolute_high" not in f0:
        missing.append("f0.absolute_high")
    f0_out = {
        "median": _safe_float(f0.get("median", 0.0)),
        "p10": _safe_float(f0.get("p10", 0.0)),
        "p90": _safe_float(f0.get("p90", 0.0)),
        "comfort_range": (
            [
                _safe_float(f0.get("comfort_range", [0.0, 0.0])[0]),
                _safe_float(f0.get("comfort_range", [0.0, 0.0])[1]),
            ]
            if isinstance(f0.get("comfort_range"), list)
            and len(f0.get("comfort_range", [])) >= 2
            else [0.0, 0.0]
        ),
        "absolute_high": _safe_float(f0.get("absolute_high", 0.0)),
    }

    formants_raw = normalized.get("formants", {})
    formants = dict(formants_raw) if isinstance(formants_raw, dict) else {}
    for key in ["f1", "f2", "f3", "vowel_space_area", "brightness"]:
        if key not in formants:
            missing.append(f"formants.{key}")
    formants_out = {
        "f1": _safe_float(formants.get("f1", 0.0)),
        "f2": _safe_float(formants.get("f2", 0.0)),
        "f3": _safe_float(formants.get("f3", 0.0)),
        "vowel_space_area": _safe_float(formants.get("vowel_space_area", 0.0)),
        "brightness": _safe_float(formants.get("brightness", 0.0)),
    }

    timbre_raw = normalized.get("timbre", {})
    timbre = dict(timbre_raw) if isinstance(timbre_raw, dict) else {}
    for key in ["hnr", "jitter", "shimmer", "breathiness", "roughness"]:
        if key not in timbre:
            missing.append(f"timbre.{key}")
    timbre_out = {
        "hnr": _safe_float(timbre.get("hnr", 0.0)),
        "jitter": _safe_float(timbre.get("jitter", 0.0)),
        "shimmer": _safe_float(timbre.get("shimmer", 0.0)),
        "breathiness": _safe_float(timbre.get("breathiness", 0.0)),
        "roughness": _safe_float(timbre.get("roughness", 0.0)),
    }

    dynamics_raw = normalized.get("dynamics", {})
    dynamics = dict(dynamics_raw) if isinstance(dynamics_raw, dict) else {}
    for key in ["intensity_range", "phrase_length"]:
        if key not in dynamics:
            missing.append(f"dynamics.{key}")
    dynamics_out = {
        "intensity_range": _safe_float(dynamics.get("intensity_range", 0.0)),
        "phrase_length": _safe_float(dynamics.get("phrase_length", 0.0)),
    }

    embedding_raw = normalized.get("embedding_clap", [])
    if "embedding_clap" not in normalized:
        missing.append("embedding_clap")
    embedding_out: list[float] = (
        [_safe_float(x) for x in embedding_raw]
        if isinstance(embedding_raw, list)
        else []
    )

    schema: dict[str, object] = {
        "f0": f0_out,
        "formants": formants_out,
        "timbre": timbre_out,
        "dynamics": dynamics_out,
        "embedding_clap": embedding_out,
    }
    return schema, missing


def _coerce_path(value: object) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def run(payload: ToolPayload) -> ToolResult:
    """Execute minimal preprocessing for acoustic_analyst."""
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv(override=False)
    except Exception:
        pass

    # Backward-compatible key bridge:
    # prefer audio_path, fallback to legacy dry_vocal_path.
    audio_path_value = payload.get("audio_path")
    if audio_path_value is None:
        audio_path_value = payload.get("dry_vocal_path")
    audio_path = _coerce_path(audio_path_value)
    input_path = audio_path.expanduser().resolve() if audio_path else None

    if input_path is None or not input_path.exists() or not input_path.is_file():
        return {
            "ok": False,
            "error": "audio_not_found",
            "input_path": str(input_path) if input_path else "",
            "preprocessed_path": str(input_path) if input_path else "",
            "demucs": {
                "requested": False,
                "available": False,
                "ran": False,
                "reason": "audio_not_found",
            },
            "parselmouth": {
                "requested": False,
                "available": False,
                "ran": False,
                "reason": "audio_not_found",
                "features": {},
            },
            "mfcc": {
                "requested": False,
                "available": False,
                "ran": False,
                "reason": "audio_not_found",
                "features": {},
            },
            "clap": {
                "requested": False,
                "available": False,
                "ran": False,
                "reason": "audio_not_found",
                "embedding": [],
            },
        }

    use_demucs = bool(payload.get("use_demucs", False))
    is_vocal = bool(payload.get("is_vocal", False))
    preprocessed_path = input_path
    demucs_meta = {
        "requested": use_demucs,
        "available": False,
        "ran": False,
        "reason": "skipped",
        "model": payload.get("demucs_model", "htdemucs_ft"),
        "output_dir": None,
        "stem_path": None,
    }
    parselmouth_meta: dict[str, object] = {
        "requested": bool(payload.get("use_parselmouth", False)),
        "available": False,
        "ran": False,
        "reason": "skipped",
        "features": {},
    }
    mfcc_meta: dict[str, object] = {
        "requested": bool(payload.get("use_librosa", False)),
        "available": False,
        "ran": False,
        "reason": "skipped",
        "features": {},
    }
    clap_meta: dict[str, object] = {
        "requested": bool(payload.get("use_clap", False)),
        "available": False,
        "ran": False,
        "reason": "skipped",
        "embedding": [],
    }

    if use_demucs and is_vocal:
        demucs_meta["reason"] = "input_is_vocal"
    elif use_demucs:
        available = _is_demucs_available()
        demucs_meta["available"] = available
        if not available:
            demucs_meta["reason"] = "demucs_unavailable"
        else:
            output_dir_value = payload.get("demucs_output_dir")
            output_dir = _coerce_path(output_dir_value)
            if output_dir is None:
                output_dir = Path(tempfile.mkdtemp(prefix="demucs_"))

            demucs_meta["output_dir"] = str(output_dir)
            try:
                stem_path = _run_demucs(
                    input_path, output_dir, str(demucs_meta["model"])
                )
            except (OSError, subprocess.CalledProcessError):
                demucs_meta["reason"] = "demucs_failed"
                return {
                    "ok": False,
                    "error": "demucs_failed",
                    "input_path": str(input_path),
                    "preprocessed_path": str(input_path),
                    "demucs": demucs_meta,
                }

            demucs_meta["ran"] = True
            demucs_meta["reason"] = "demucs_ran"
            demucs_meta["stem_path"] = str(stem_path)
            preprocessed_path = stem_path

    if bool(parselmouth_meta["requested"]):
        available = _is_parselmouth_available()
        parselmouth_meta["available"] = available
        if not available:
            parselmouth_meta["reason"] = "parselmouth_unavailable"
        else:
            try:
                parselmouth_meta["features"] = _extract_parselmouth_features(
                    preprocessed_path
                )
            except Exception as exc:
                # Non-fatal fallback: keep pipeline running with default profile.
                parselmouth_meta["reason"] = "parselmouth_failed_fallback"
                parselmouth_meta["warning"] = str(exc)
                parselmouth_meta["features"] = {
                    "f0": {"median": 0.0, "p10": 0.0, "p90": 0.0},
                    "formants": {"f1": 0.0, "f2": 0.0, "f3": 0.0},
                    "timbre": {"hnr": 0.0, "jitter": 0.0, "shimmer": 0.0},
                    "dynamics": {"intensity_range": 0.0},
                }
            else:
                parselmouth_meta["ran"] = True
                parselmouth_meta["reason"] = "parselmouth_ran"

    if bool(mfcc_meta["requested"]):
        available = _is_librosa_available()
        mfcc_meta["available"] = available
        if not available:
            mfcc_meta["reason"] = "librosa_unavailable"
        else:
            try:
                n_mfcc = _safe_int(payload.get("mfcc_n", 13), 13)
                mfcc_meta["features"] = _extract_mfcc_features(
                    preprocessed_path, n_mfcc
                )
            except Exception:
                mfcc_meta["reason"] = "librosa_failed"
                return {
                    "ok": False,
                    "error": "librosa_failed",
                    "input_path": str(input_path),
                    "preprocessed_path": str(preprocessed_path),
                    "demucs": demucs_meta,
                    "parselmouth": parselmouth_meta,
                    "mfcc": mfcc_meta,
                    "clap": clap_meta,
                }
            mfcc_meta["ran"] = True
            mfcc_meta["reason"] = "mfcc_ran"

    if bool(clap_meta["requested"]):
        available = _is_clap_available()
        clap_meta["available"] = available
        if not available:
            clap_meta["reason"] = "clap_unavailable"
        else:
            try:
                clap_meta["embedding"] = _extract_clap_embedding(preprocessed_path)
            except Exception:
                clap_meta["reason"] = "clap_failed"
                return {
                    "ok": False,
                    "error": "clap_failed",
                    "input_path": str(input_path),
                    "preprocessed_path": str(preprocessed_path),
                    "demucs": demucs_meta,
                    "parselmouth": parselmouth_meta,
                    "mfcc": mfcc_meta,
                    "clap": clap_meta,
                }
            clap_meta["ran"] = True
            clap_meta["reason"] = "clap_ran"

    raw_parselmouth_features = parselmouth_meta.get("features", {})
    parselmouth_features: dict[str, object] = (
        dict(raw_parselmouth_features)
        if isinstance(raw_parselmouth_features, dict)
        else {}
    )

    raw_clap_embedding = clap_meta.get("embedding", [])
    clap_embedding: list[float] = (
        [_safe_float(value) for value in raw_clap_embedding]
        if isinstance(raw_clap_embedding, list)
        else []
    )

    voice_profile = _voice_profile_from_features(parselmouth_features, clap_embedding)
    voice_profile, missing_fields = _normalize_voice_profile_schema(voice_profile)

    voice_profile_path_value = payload.get("voice_profile_path")
    voice_profile_path = _coerce_path(voice_profile_path_value)
    resolved_voice_profile_path = (
        voice_profile_path.expanduser().resolve() if voice_profile_path else None
    )

    if resolved_voice_profile_path is not None:
        resolved_voice_profile_path.parent.mkdir(parents=True, exist_ok=True)
        _ = resolved_voice_profile_path.write_text(
            json.dumps(voice_profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    degraded = (
        str(parselmouth_meta.get("reason", "")).startswith("parselmouth_failed")
        or str(mfcc_meta.get("reason", "")).endswith("_failed")
        or str(clap_meta.get("reason", "")).endswith("_failed")
    )

    return {
        "ok": True,
        "input_path": str(input_path),
        "preprocessed_path": str(preprocessed_path),
        "demucs": demucs_meta,
        "parselmouth": parselmouth_meta,
        "mfcc": mfcc_meta,
        "clap": clap_meta,
        "voice_profile": voice_profile,
        "voice_profile_path": (
            str(resolved_voice_profile_path) if resolved_voice_profile_path else ""
        ),
        "degraded": degraded,
        "warnings": [
            value
            for value in [
                parselmouth_meta.get("warning"),
                mfcc_meta.get("warning"),
                clap_meta.get("warning"),
            ]
            if isinstance(value, str) and value
        ],
        "missing_profile_fields": missing_fields,
    }
