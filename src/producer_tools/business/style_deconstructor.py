"""Reference audio decomposition pipeline for style_deconstructor tool."""

from __future__ import annotations

import importlib.util
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from ..contracts import ToolPayload, ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "style_deconstructor"


def _compute_target_words(
    bars: int,
    beats_per_bar: int,
    bpm: float,
    avg_syllables_per_beat: float = 1.2,
) -> int:
    """Compute beat-aligned target words with bounded range."""
    safe_bars = max(1, int(bars))
    safe_beats = max(1, int(beats_per_bar))
    safe_bpm = bpm if isinstance(bpm, (int, float)) and bpm > 0 else 100.0
    raw = round(
        safe_bars * safe_beats * (float(safe_bpm) / 60.0) * avg_syllables_per_beat
    )
    return max(8, min(48, int(raw)))


def _is_demucs_available() -> bool:
    return (
        importlib.util.find_spec("demucs") is not None
        or shutil.which("demucs") is not None
    )


def _run_demucs_6s(input_path: Path, output_dir: Path, model: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = ["demucs", "-n", model, "-o", str(output_dir), str(input_path)]
    subprocess.run(command, check=True, capture_output=True)

    stem_names = ["vocals", "drums", "bass", "guitar", "piano", "other"]
    result: dict[str, str] = {}
    model_dir = output_dir / model / input_path.stem
    for name in stem_names:
        stem_file = model_dir / f"{name}.wav"
        result[name] = (
            str(stem_file.resolve())
            if stem_file.exists()
            else str(input_path.resolve())
        )
    return result


def _coerce_path(value: object) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _is_librosa_available() -> bool:
    return importlib.util.find_spec("librosa") is not None


def _load_audio_mono(input_path: Path) -> tuple[np.ndarray, int]:
    """Prefer soundfile for FLAC/MP3 decode, fallback to librosa.load."""
    import librosa

    try:
        import soundfile as sf

        y, sr = sf.read(str(input_path), dtype="float32", always_2d=False)
        if isinstance(y, np.ndarray) and y.ndim > 1:
            y = np.mean(y, axis=1)
        y_np = np.asarray(y, dtype=np.float32)
        return y_np, int(sr)
    except Exception:
        y, sr = librosa.load(str(input_path), sr=None, mono=True)
        return np.asarray(y, dtype=np.float32), int(sr)


def _extract_tempo_key(input_path: Path) -> dict[str, object]:
    """Extract BPM, musical key, and song structure from audio."""
    beats_per_bar = 4
    fallback_bpm = 100.0
    fallback_sections: list[dict[str, object]] = []
    for lbl in ["verse", "pre_chorus", "chorus", "verse", "bridge", "chorus"]:
        bars = 4
        beats = bars * beats_per_bar
        fallback_sections.append(
            {
                "label": lbl,
                "bars": bars,
                "beats": beats,
                "target_words": _compute_target_words(
                    bars=bars,
                    beats_per_bar=beats_per_bar,
                    bpm=fallback_bpm,
                ),
            }
        )

    default: dict[str, object] = {
        "bpm": 0.0,
        "key": "C",
        "scale": "major",
        "structure": [],
        "lyric_beat_budget": {
            "beats_per_bar": beats_per_bar,
            "bpm": fallback_bpm,
            "total_beats": len(fallback_sections) * 16,
            "sections": fallback_sections,
        },
    }

    if not _is_librosa_available():
        logger.debug("librosa not available, returning default tempo_key")
        return default

    try:
        import librosa  # type: ignore[import-untyped]

        y, sr = _load_audio_mono(input_path)

        if len(y) == 0:
            return default

        # BPM extraction
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm_val = float(np.atleast_1d(tempo)[0]) if np.ndim(tempo) > 0 else float(tempo)

        # Key detection via chroma
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_avg = np.mean(chroma, axis=1)
        key_idx = int(np.argmax(chroma_avg))

        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        detected_key = note_names[key_idx]

        # Major/minor heuristic: relative major/minor check
        minor_idx = (key_idx + 9) % 12
        if chroma_avg[minor_idx] > chroma_avg[key_idx] * 0.8:
            scale = "minor"
        else:
            scale = "major"

        # Structure detection via onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        if len(onset_env) > 0:
            frames_per_segment = max(1, len(onset_env) // 8)
            n_segments = max(1, len(onset_env) // frames_per_segment)
            structure: list[dict[str, object]] = []
            for i in range(n_segments):
                start_frame = i * frames_per_segment
                end_frame = min((i + 1) * frames_per_segment, len(onset_env))
                seg_energy = float(np.mean(onset_env[start_frame:end_frame]))
                label = "chorus" if seg_energy > np.mean(onset_env) else "verse"
                structure.append(
                    {
                        "index": i,
                        "label": label,
                        "energy": seg_energy,
                    }
                )
        else:
            structure = []

        structure_sections = structure
        bpm_for_budget = bpm_val if bpm_val > 0 else fallback_bpm
        total_beats = max(0, len(structure_sections) * 16)
        section_budgets: list[dict[str, object]] = []
        if structure_sections:
            for seg in structure_sections:
                if not isinstance(seg, dict):
                    continue
                label = str(seg.get("label", "verse"))
                bars = 4
                beats = bars * beats_per_bar
                section_budgets.append(
                    {
                        "label": label,
                        "bars": bars,
                        "beats": beats,
                        "target_words": _compute_target_words(
                            bars=bars,
                            beats_per_bar=beats_per_bar,
                            bpm=bpm_for_budget,
                        ),
                    }
                )
        else:
            fallback_labels = [
                "verse",
                "pre_chorus",
                "chorus",
                "verse",
                "bridge",
                "chorus",
            ]
            for lbl in fallback_labels:
                bars = 4
                beats = bars * beats_per_bar
                section_budgets.append(
                    {
                        "label": lbl,
                        "bars": bars,
                        "beats": beats,
                        "target_words": _compute_target_words(
                            bars=bars,
                            beats_per_bar=beats_per_bar,
                            bpm=bpm_for_budget,
                        ),
                    }
                )
            total_beats = len(section_budgets) * beats_per_bar * 4

        return {
            "bpm": round(bpm_val, 1),
            "key": detected_key,
            "scale": scale,
            "structure": structure_sections,
            "lyric_beat_budget": {
                "beats_per_bar": beats_per_bar,
                "bpm": round(bpm_for_budget, 1),
                "total_beats": total_beats,
                "sections": section_budgets,
            },
        }

    except Exception:
        logger.debug("librosa analysis failed, returning default tempo_key")
        return default


def _extract_instrumentation(
    input_path: Path, stem_paths: dict[str, str]
) -> dict[str, object]:
    """Detect instrumentation per stem using spectral features.

    Returns per-stem format matching PRD:
      {stem_name: {presence: bool, role: str}}
    """
    default: dict[str, object] = {
        stem: {"presence": False, "role": None}
        for stem in ["vocals", "drums", "bass", "guitar", "piano", "other"]
    }

    if not _is_librosa_available():
        return default

    try:
        import librosa  # type: ignore[import-untyped]

        result: dict[str, object] = {
            stem: {"presence": False, "role": None}
            for stem in ["vocals", "drums", "bass", "guitar", "piano", "other"]
        }

        # Analyze vocals stem if available
        vocal_path_str = stem_paths.get("vocals")
        if vocal_path_str:
            vocal_path = Path(vocal_path_str)
            if vocal_path.exists() and vocal_path.stat().st_size > 1000:
                try:
                    y, sr = _load_audio_mono(vocal_path)
                    if len(y) > 0:
                        zcr = librosa.feature.zero_crossing_rate(y)
                        avg_zcr = float(np.mean(zcr))
                        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                        mfcc_std = float(np.std(mfccs))

                        result["vocals"] = {
                            "presence": True,
                            "role": "lead_vocal",
                        }
                        # High ZCR = drums/percussion
                        if avg_zcr > 0.1:
                            result["drums"] = {"presence": True, "role": "rhythm"}
                        # MFCC variance indicates vocal-like timbre
                        if mfcc_std > 5:
                            result["vocals"] = {"presence": True, "role": "lead_vocal"}
                except Exception:
                    pass

        # Analyze non-vocal stems for guitar/piano/bass
        for stem_name in ["guitar", "piano", "bass"]:
            stem_path_str = stem_paths.get(stem_name)
            if stem_path_str:
                stem_path = Path(stem_path_str)
                if stem_path.exists() and stem_path.stat().st_size > 1000:
                    try:
                        y, sr = _load_audio_mono(stem_path)
                        if len(y) > 0:
                            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
                            avg_centroid = float(np.mean(centroid))
                            bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
                            avg_bw = float(np.mean(bandwidth))

                            if avg_centroid > 2500:
                                result[stem_name] = {
                                    "presence": True,
                                    "role": "melody/harmony",
                                }
                            elif stem_name == "bass" or avg_centroid < 1500:
                                result["bass"] = {
                                    "presence": True,
                                    "role": "foundation",
                                }
                    except Exception:
                        pass

        return result

    except Exception:
        return default


def _extract_energy_curve(
    input_path: Path, segments: int = 16
) -> list[dict[str, object]]:
    """Extract energy curve over time segments."""
    if not _is_librosa_available():
        return []

    try:
        import librosa  # type: ignore[import-untyped]

        y, sr = _load_audio_mono(input_path)

        if len(y) == 0:
            return []

        # RMS energy
        rms = librosa.feature.rms(y=y)
        rms_flat = rms.flatten()

        if len(rms_flat) == 0:
            return []

        # Divide into segments
        segment_size = max(1, len(rms_flat) // segments)
        energy_curve: list[dict[str, object]] = []

        for i in range(segments):
            start = i * segment_size
            end = min((i + 1) * segment_size, len(rms_flat))

            if start >= len(rms_flat):
                break

            segment_energy = float(np.mean(rms_flat[start:end]))
            time_sec = (start / len(rms_flat)) * (len(y) / sr)

            energy_curve.append(
                {
                    "time": round(time_sec, 2),
                    "energy": round(segment_energy, 4),
                }
            )

        return energy_curve

    except Exception:
        return []


def run(payload: ToolPayload) -> ToolResult:
    """Execute the style_deconstructor decomposition pipeline."""
    audio_path_value = payload.get("reference_audio_path")
    audio_path = _coerce_path(audio_path_value)
    input_path = audio_path.expanduser().resolve() if audio_path else None

    if input_path is None or not input_path.exists() or not input_path.is_file():
        return {
            "ok": False,
            "error": "reference_audio_not_found",
            "input_path": str(input_path) if input_path else "",
            "demucs": {
                "requested": False,
                "available": False,
                "ran": False,
                "reason": "reference_audio_not_found",
            },
            "stems": {},
        }

    use_demucs = bool(payload.get("use_demucs", False))
    demucs_model = str(payload.get("demucs_model", "htdemucs_6s"))

    demucs_meta: dict[str, object] = {
        "requested": use_demucs,
        "available": False,
        "ran": False,
        "reason": "skipped",
        "model": demucs_model,
        "output_dir": None,
    }
    stems: dict[str, str] = {}

    if use_demucs:
        available = _is_demucs_available()
        demucs_meta["available"] = available
        if not available:
            demucs_meta["reason"] = "demucs_unavailable"
            return {
                "ok": False,
                "error": "demucs_unavailable",
                "input_path": str(input_path),
                "demucs": demucs_meta,
                "stems": {},
            }
        else:
            output_dir_value = payload.get("demucs_output_dir")
            output_dir = _coerce_path(output_dir_value)
            if output_dir is None:
                output_dir = Path(tempfile.mkdtemp(prefix="demucs_6s_"))
            demucs_meta["output_dir"] = str(output_dir)
            try:
                stems = _run_demucs_6s(input_path, output_dir, demucs_model)
            except (OSError, subprocess.CalledProcessError):
                demucs_meta["reason"] = "demucs_failed"
                return {
                    "ok": False,
                    "error": "demucs_failed",
                    "input_path": str(input_path),
                    "demucs": demucs_meta,
                    "stems": {},
                }
            demucs_meta["ran"] = True
            demucs_meta["reason"] = "demucs_ran"

    tempo_key = _extract_tempo_key(input_path)
    instrumentation = _extract_instrumentation(input_path, stems)
    energy_curve = _extract_energy_curve(input_path)

    # Build reference_dna output
    reference_dna: dict[str, object] = {
        "tempo": tempo_key.get("bpm", 0.0),
        "key": tempo_key.get("key", "C"),
        "scale": tempo_key.get("scale", "major"),
        "structure": tempo_key.get("structure", []),
        "lyric_beat_budget": tempo_key.get("lyric_beat_budget", {}),
        "instrumentation": instrumentation,
        "energy_curve": energy_curve,
        "vocal_pitch_range_midi": None,
        "vocal_melismatic_density": 0.0,
        "stems_dir": str(demucs_meta.get("output_dir", "")) if use_demucs else "",
    }

    # Handle optional reference_dna_output_path
    reference_dna_path_value = payload.get("reference_dna_output_path")
    reference_dna_path = _coerce_path(reference_dna_path_value)
    if reference_dna_path is not None:
        try:
            reference_dna_path.parent.mkdir(parents=True, exist_ok=True)
            reference_dna_path.write_text(
                json.dumps(reference_dna, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    return {
        "ok": True,
        "input_path": str(input_path),
        "demucs": demucs_meta,
        "stems": stems,
        "tempo_key": tempo_key,
        "reference_dna": reference_dna,
        "instrumentation": instrumentation,
        "energy_curve": energy_curve,
        "reference_dna_path": str(reference_dna_path) if reference_dna_path else "",
    }
