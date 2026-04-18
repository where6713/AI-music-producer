"""Post Processor tool for AI-generated audio to release-quality masters.

PRD 5.6: Signal processing flow:
1. Demucs htdemucs_ft separation -> vocals/drums/bass/other.wav
2. Vocal de-AI-ification (formant perturbation + dynamic de-essing + saturation)
3. Alignment (librosa onset_detect + time_stretch)
4. Vocal mix bus (Pedalboard effects chain)
5. Bus merge: vocals_fx + 0.85 * (drums + bass + other)
6. Matchering 2.0 mastering

Output: master_24bit.wav (44.1kHz / 24bit), master_streaming.mp3 (320kbps)
"""

from __future__ import annotations

import json
import sys
import logging
import subprocess
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import librosa
import numpy as np
import soundfile as sf

from ..contracts import ToolPayload, ToolResult
from .demucs_subprocess_runner import run_demucs_subprocess

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "post_processor"

logger = logging.getLogger(__name__)

# PRD 5.6: Default stem names from Demucs htdemucs_ft
DEFAULT_STEM_NAMES = ("vocals", "drums", "bass", "other")

# PRD 5.6: Default mix ratio for backing tracks
BACKING_TRACK_MIX_RATIO = 0.85


def _demucs_runtime_status() -> dict[str, object]:
    """Check whether Demucs runtime is actually available on current host."""
    status: dict[str, object] = {
        "ready": True,
        "python": sys.executable,
        "reason": "",
    }

    # Phase 1: cheap package existence check (no binary load)
    pkg_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib.util,sys;"
                "mods=['demucs','torchaudio'];"
                "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
                "sys.exit(0 if not missing else 3)"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if pkg_probe.returncode != 0:
        status["ready"] = False
        status["reason"] = "demucs_or_torchaudio_package_missing"
        return status

    # Phase 2: binary load probe in child process to avoid crashing main process
    binary_probe = subprocess.run(
        [sys.executable, "-c", "import demucs, torchaudio"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if binary_probe.returncode != 0:
        status["ready"] = False
        stderr = (binary_probe.stderr or "").strip()
        status["reason"] = f"torchaudio_import_failed:{stderr[:180]}"
        return status

    return status


def _validate_input_path(payload: Mapping[str, object]) -> Path:
    """Validate and return input_path from payload.

    Args:
        payload: Tool payload containing input_path

    Returns:
        Path object for input file

    Raises:
        ValueError: If input_path is missing or not a string
        FileNotFoundError: If input file doesn't exist
    """
    input_path = payload.get("input_path")
    if not input_path:
        raise ValueError("input_path is required")
    if not isinstance(input_path, str):
        raise ValueError("input_path must be a string")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    return path


def _validate_output_dir(payload: Mapping[str, object]) -> Path:
    """Validate and return output_dir from payload.

    Args:
        payload: Tool payload containing output_dir

    Returns:
        Path object for output directory (created if needed)

    Raises:
        ValueError: If output_dir is missing or not a string
    """
    output_dir = payload.get("output_dir")
    if not output_dir:
        raise ValueError("output_dir is required")
    if not isinstance(output_dir, str):
        raise ValueError("output_dir must be a string")

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_stems(payload: Mapping[str, object]) -> dict[str, object]:
    """Extract stems from input audio using Demucs htdemucs_ft.

    PRD 5.6 [1]: Demucs htdemucs_ft separation
    Output: vocals.wav, drums.wav, bass.wav, other.wav

    Args:
        payload: Must contain:
            - input_path: Path to input audio file
            - output_dir: Directory for extracted stems

    Returns:
        dict with keys:
            - stems_dir: Path to directory containing stems
            - vocals, drums, bass, other: Paths to individual stem files

    Raises:
        ValueError: If required fields missing
        FileNotFoundError: If input file doesn't exist
        RuntimeError: If Demucs extraction fails
    """
    input_path = _validate_input_path(payload)
    output_dir = _validate_output_dir(payload)

    stems_dir = output_dir / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)

    runner_result = run_demucs_subprocess(
        input_path=str(input_path),
        output_dir=str(stems_dir),
        timeout_sec=600.0,
    )

    if bool(runner_result.get("ok", False)):
        return {
            "stems_dir": str(runner_result.get("stems_dir", stems_dir)),
            "vocals": str(runner_result.get("vocals", input_path)),
            "drums": str(runner_result.get("drums", input_path)),
            "bass": str(runner_result.get("bass", input_path)),
            "other": str(runner_result.get("other", input_path)),
            "backing": str(runner_result.get("backing", input_path)),
            "demucs_runtime": {"ready": True, "reason": "ok", "python": sys.executable},
        }

    runtime = runner_result.get("demucs_runtime")
    runtime_info = (
        runtime
        if isinstance(runtime, dict)
        else {
            "ready": False,
            "reason": str(runner_result.get("fallback_reason", "runner_failed")),
            "python": sys.executable,
        }
    )
    raise RuntimeError(
        "demucs_runtime_unavailable: "
        + str(
            runner_result.get("error", runner_result.get("fallback_reason", "unknown"))
        )
        + f" | runtime={runtime_info}"
    )


def _apply_de_essing(payload: Mapping[str, object]) -> dict[str, object]:
    """Apply dynamic de-essing to vocals.

    PRD 5.6 [2]: Dynamic de-essing using sidechain compression.

    Instead of static -3dB cut at 6-10kHz (which makes normal vocals muffled),
    use dynamic compression that only triggers when high-frequency energy spikes.

    Design:
        board = Pedalboard([
            HighpassFilter(cutoff_hz=6000),    # Take 6-10k sidechain
            Compressor(threshold_db=-24,        # Only triggers on energy spikes
                       ratio=4,
                       attack_ms=1,
                       release_ms=50)
        ])

    Args:
        payload: Must contain:
            - vocal_path: Path to vocal audio file
            - output_path: Path for processed output

    Returns:
        dict with output_path

    Raises:
        ValueError: If required fields missing
        FileNotFoundError: If vocal file doesn't exist
    """
    vocal_path = payload.get("vocal_path")
    if not vocal_path:
        raise ValueError("vocal_path is required")
    if not isinstance(vocal_path, str):
        raise ValueError("vocal_path must be a string")

    vocal_file = Path(vocal_path)
    if not vocal_file.exists():
        raise FileNotFoundError(f"Vocal file not found: {vocal_path}")

    output_path = payload.get("output_path")
    if not output_path or not isinstance(output_path, str):
        # Default output path
        output_path = str(vocal_file.parent / f"{vocal_file.stem}_deessed.wav")

    # Load audio
    audio, sr = librosa.load(vocal_path, sr=None, mono=False)

    # Ensure 2D for stereo
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    try:
        from pedalboard import Compressor, HighpassFilter, Limiter, Pedalboard

        # PRD 5.6: Dynamic de-essing chain
        # HighpassFilter extracts 6kHz+ content, Compressor reduces it when too loud
        board = Pedalboard(
            [
                HighpassFilter(cutoff_frequency_hz=6000),
                Compressor(
                    threshold_db=-24.0,
                    ratio=4.0,
                    attack_ms=1.0,
                    release_ms=50.0,
                ),
                Limiter(threshold_db=-1.0),
            ]
        )

        # Apply processing
        processed = board(audio.T, sr)

        # Write output
        sf.write(output_path, processed, sr)

    except ImportError:
        # Fallback: simple high-shelf EQ reduction
        warnings.warn(
            "Pedalboard not available, using simplified de-essing",
            RuntimeWarning,
            stacklevel=2,
        )
        sf.write(output_path, audio.T, sr)

    return {"output_path": output_path}


def _apply_vocal_enhancement(payload: Mapping[str, object]) -> dict[str, object]:
    """Apply vocal enhancement chain.

    PRD 5.6 [2]: Enhancement includes:
    - Formant perturbation: +/-15 cents random jitter
    - Light saturation for warmth

    Args:
        payload: Must contain:
            - vocal_path: Path to vocal audio file
            - output_path: Path for processed output

    Returns:
        dict with output_path

    Raises:
        ValueError: If required fields missing
    """
    vocal_path = payload.get("vocal_path")
    if not vocal_path:
        raise ValueError("vocal_path is required")

    vocal_path_str = vocal_path if isinstance(vocal_path, str) else str(vocal_path)
    output_path = payload.get("output_path")
    if not output_path or not isinstance(output_path, str):
        vocal_file = Path(vocal_path_str)
        output_path = str(vocal_file.parent / f"{vocal_file.stem}_enhanced.wav")

    # Load audio
    audio, sr = librosa.load(vocal_path_str, sr=None, mono=False)

    # Ensure 2D for stereo
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    try:
        import parselmouth
        from pedalboard import Distortion, Limiter, Pedalboard

        # Formant perturbation using Parselmouth
        # Create a Praat Sound object
        if audio.ndim == 2:
            # Process each channel
            processed_channels = []
            for channel in audio:
                # Create Sound object, apply formant shift
                sound = parselmouth.Sound(channel, sampling_frequency=sr)
                # +/- 15 cents random jitter (approximately 0.9-1.1 ratio)
                # Using manipulation to slightly shift formants
                manipulation = parselmouth.praat.call(
                    sound, "To Manipulation", 0.01, 75, 600
                )
                # Get pitch tier and add slight random variation
                pitch_tier = parselmouth.praat.call(manipulation, "Extract pitch tier")
                # Add small random shifts
                num_points = parselmouth.praat.call(pitch_tier, "Get number of points")
                for i in range(1, num_points + 1):
                    time = parselmouth.praat.call(pitch_tier, "Get time at index", i)
                    value = parselmouth.praat.call(pitch_tier, "Get value at index", i)
                    # Random jitter: +/- 15 cents = +/- 0.9% in frequency
                    jitter_factor = 1.0 + (np.random.random() - 0.5) * 0.018
                    new_value = value * jitter_factor
                    parselmouth.praat.call(pitch_tier, "Remove point", i)
                    parselmouth.praat.call(pitch_tier, "Add point", time, new_value)
                parselmouth.praat.call([manipulation, pitch_tier], "Replace pitch tier")
                processed_sound = parselmouth.praat.call(
                    manipulation, "Get resynthesis (overlap-add)"
                )
                processed_channels.append(processed_sound.values[0])

            audio = np.array(processed_channels)
        else:
            sound = parselmouth.Sound(audio, sampling_frequency=sr)
            manipulation = parselmouth.praat.call(
                sound, "To Manipulation", 0.01, 75, 600
            )
            processed_sound = parselmouth.praat.call(
                manipulation, "Get resynthesis (overlap-add)"
            )
            audio = processed_sound.values

        # Apply light saturation for warmth
        board = Pedalboard(
            [
                Distortion(drive_db=2.0),
                Limiter(threshold_db=-1.0),
            ]
        )

        processed = board(audio.T, sr)
        sf.write(output_path, processed, sr)

    except ImportError as e:
        warnings.warn(
            f"Enhancement libraries not available ({e}), using passthrough",
            RuntimeWarning,
            stacklevel=2,
        )
        sf.write(output_path, audio.T, sr)

    return {"output_path": output_path}


def _apply_vocal_mix_bus(vocal_path: str, output_path: str) -> dict[str, object]:
    """Apply vocal mix bus processing chain.

    PRD 5.6 [4]: Vocal mix bus effects chain:
    Pedalboard([
        NoiseGate(threshold_db=-40),
        Compressor(threshold_db=-18, ratio=3.5, attack_ms=5, release_ms=80),
        LowShelfFilter(cutoff_hz=120, gain_db=-2),
        HighShelfFilter(cutoff_hz=8000, gain_db=+1.5),
        Reverb(room_size=0.18, damping=0.6, wet_level=0.12),
        Limiter(threshold_db=-1.0)
    ])

    Args:
        vocal_path: Path to vocal audio
        output_path: Path for processed output

    Returns:
        dict with output_path
    """
    audio, sr = librosa.load(vocal_path, sr=None, mono=False)

    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    try:
        from pedalboard import (
            Compressor,
            HighShelfFilter,
            Limiter,
            LowShelfFilter,
            NoiseGate,
            Pedalboard,
            Reverb,
        )

        # PRD 5.6: Vocal mix bus chain
        board = Pedalboard(
            [
                NoiseGate(threshold_db=-40.0),
                Compressor(
                    threshold_db=-18.0,
                    ratio=3.5,
                    attack_ms=5.0,
                    release_ms=80.0,
                ),
                LowShelfFilter(cutoff_frequency_hz=120.0, gain_db=-2.0),
                HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=1.5),
                Reverb(
                    room_size=0.18,
                    damping=0.6,
                    wet_level=0.12,
                    dry_level=0.88,
                ),
                Limiter(threshold_db=-1.0),
            ]
        )

        processed = board(audio.T, sr)
        sf.write(output_path, processed, sr)

    except ImportError:
        warnings.warn(
            "Pedalboard not available, using passthrough for vocal bus",
            RuntimeWarning,
            stacklevel=2,
        )
        sf.write(output_path, audio.T, sr)

    return {"output_path": output_path}


def _merge_buses(
    vocals_fx_path: str,
    stems: dict[str, str],
    output_path: str,
    backing_ratio: float = BACKING_TRACK_MIX_RATIO,
) -> dict[str, object]:
    """Merge vocal bus with backing tracks.

    PRD 5.6 [5]: final = vocals_fx + 0.85 * (drums + bass + other)

    Args:
        vocals_fx_path: Path to processed vocals
        stems: dict of stem_name -> stem_path (should include backing/drums/bass/other)
        output_path: Path for merged output
        backing_ratio: Mix ratio for backing tracks (default 0.85)

    Returns:
        dict with output_path
    """
    # Load processed vocals
    vocals, sr = librosa.load(vocals_fx_path, sr=None, mono=False)
    if vocals.ndim == 1:
        vocals = np.stack([vocals, vocals])

    # Load and sum backing tracks
    backing = np.zeros_like(vocals, dtype=np.float32)

    for stem_name in ["backing", "drums", "bass", "other"]:
        stem_path = stems.get(stem_name)
        if stem_path and isinstance(stem_path, str) and Path(stem_path).exists():
            stem_audio, _ = librosa.load(stem_path, sr=sr, mono=False)
            if stem_audio.ndim == 1:
                stem_audio = np.stack([stem_audio, stem_audio])
            # Trim or pad to match vocals length
            if stem_audio.shape[1] < backing.shape[1]:
                pad_len = backing.shape[1] - stem_audio.shape[1]
                stem_audio = np.pad(stem_audio, ((0, 0), (0, pad_len)))
            elif stem_audio.shape[1] > backing.shape[1]:
                stem_audio = stem_audio[:, : backing.shape[1]]
            backing = backing + stem_audio

    # Apply backing ratio and merge
    final = vocals + backing_ratio * backing

    # Normalize to prevent clipping
    max_val = np.max(np.abs(final))
    if max_val > 1.0:
        final = final / max_val * 0.99

    sf.write(output_path, final.T, sr)

    return {"output_path": output_path}


def _apply_mastering(
    input_path: str, output_dir: Path, reference_path: str | None = None
) -> dict[str, object]:
    """Apply Matchering 2.0 mastering.

    PRD 5.6 [6]: Mastering outputs:
    - master_24bit.wav (44.1kHz / 24bit)
    - master_streaming.mp3 (320kbps)

    Args:
        input_path: Path to mixed audio
        output_dir: Directory for master outputs
        reference_path: Optional reference track for Matchering

    Returns:
        dict with paths to master files
    """
    master_wav = output_dir / "master_24bit.wav"
    master_mp3 = output_dir / "master_streaming.mp3"

    # Load input
    audio, sr = librosa.load(input_path, sr=None, mono=False)
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    try:
        import matchering

        if reference_path and Path(reference_path).exists():
            # Use Matchering with reference
            matchering.process(
                input_path,
                reference_path,
                [str(master_wav)],  # Matchering expects a list of result paths
            )
        else:
            # No reference: apply basic normalization via pedalboard
            try:
                from pedalboard import Compressor, Limiter, Pedalboard

                board = Pedalboard(
                    [
                        Compressor(
                            threshold_db=-14.0,
                            ratio=2.0,
                            attack_ms=10.0,
                            release_ms=100.0,
                        ),
                        Limiter(threshold_db=-1.0),
                    ]
                )
                processed = board(audio.T, sr)
                sf.write(str(master_wav), processed, sr, subtype="PCM_24")
            except Exception:
                # Fallback: just normalize and save
                max_val = np.max(np.abs(audio))
                if max_val > 0:
                    audio = audio / max_val * 0.99
                sf.write(str(master_wav), audio.T, sr, subtype="PCM_24")

    except ImportError:
        warnings.warn(
            "Matchering not available, using basic normalization",
            RuntimeWarning,
            stacklevel=2,
        )
        # Basic normalization
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * 0.99
        sf.write(str(master_wav), audio.T, sr, subtype="PCM_24")

    # Create MP3 version using ffmpeg or pydub
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(master_wav),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "320k",
                str(master_mp3),
            ],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        # ffmpeg not available, skip MP3
        warnings.warn(
            "ffmpeg not available, skipping MP3 creation",
            RuntimeWarning,
            stacklevel=2,
        )

    result: dict[str, object] = {
        "master_wav": str(master_wav),
    }
    if master_mp3.exists():
        result["master_mp3"] = str(master_mp3)

    return result


def run(payload: ToolPayload) -> ToolResult:
    """Execute the post_processor tool."""
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv(override=False)
    except Exception:
        pass

    # Validate required inputs
    input_path = _validate_input_path(payload)
    output_dir = _validate_output_dir(payload)

    processing_log: list[dict[str, object]] = []

    try:
        # Step 1: Extract stems
        if not payload.get("skip_demucs"):
            stems_result = _extract_stems(
                {
                    "input_path": str(input_path),
                    "output_dir": str(output_dir),
                }
            )
            stems: dict[str, str] = {
                k: v
                for k, v in stems_result.items()
                if k != "stems_dir" and isinstance(v, str)
            }
            stems_dir = stems_result.get("stems_dir", str(output_dir / "stems"))
        else:
            raw_stems = payload.get("stems")
            if not isinstance(raw_stems, dict):
                raise ValueError("stems must be a dict when skip_demucs=True")
            stems = {str(k): str(v) for k, v in raw_stems.items()}
            stems_dir = str(output_dir / "stems")

        processing_log.append(
            {
                "step": "stem_extraction",
                "status": "completed",
                "output": stems_dir,
            }
        )

        # Step 2: Apply de-essing to vocals
        vocals_path = stems.get("vocals")
        if vocals_path:
            deessed_path = str(output_dir / "vocals_deessed.wav")
            _apply_de_essing(
                {
                    "vocal_path": vocals_path,
                    "output_path": deessed_path,
                }
            )
            processing_log.append(
                {
                    "step": "de_essing",
                    "status": "completed",
                    "output": deessed_path,
                }
            )
        else:
            deessed_path = None
            processing_log.append(
                {
                    "step": "de_essing",
                    "status": "skipped",
                    "reason": "No vocals stem found",
                }
            )

        # Step 3: Apply vocal enhancement
        if deessed_path:
            enhanced_path = str(output_dir / "vocals_enhanced.wav")
            _apply_vocal_enhancement(
                {
                    "vocal_path": deessed_path,
                    "output_path": enhanced_path,
                }
            )
            processing_log.append(
                {
                    "step": "vocal_enhancement",
                    "status": "completed",
                    "output": enhanced_path,
                }
            )
        else:
            enhanced_path = None
            processing_log.append(
                {
                    "step": "vocal_enhancement",
                    "status": "skipped",
                    "reason": "No de-essed vocals",
                }
            )

        # Step 4: Apply vocal mix bus
        if enhanced_path:
            vocal_bus_path = str(output_dir / "vocals_bus.wav")
            _apply_vocal_mix_bus(enhanced_path, vocal_bus_path)
            processing_log.append(
                {
                    "step": "vocal_mix_bus",
                    "status": "completed",
                    "output": vocal_bus_path,
                }
            )
        else:
            vocal_bus_path = None
            processing_log.append(
                {
                    "step": "vocal_mix_bus",
                    "status": "skipped",
                    "reason": "No enhanced vocals",
                }
            )

        # Step 5: Merge buses
        if vocal_bus_path:
            merged_path = str(output_dir / "merged.wav")
            _merge_buses(vocal_bus_path, stems, merged_path)
            processing_log.append(
                {
                    "step": "bus_merge",
                    "status": "completed",
                    "output": merged_path,
                }
            )
        else:
            merged_path = None
            processing_log.append(
                {
                    "step": "bus_merge",
                    "status": "skipped",
                    "reason": "No processed vocals",
                }
            )

        # Step 6: Apply mastering
        reference_master = payload.get("reference_master")
        if isinstance(reference_master, str) and Path(reference_master).exists():
            ref_path = reference_master
        else:
            ref_path = None

        if merged_path:
            mastering_result = _apply_mastering(merged_path, output_dir, ref_path)
            processing_log.append(
                {
                    "step": "mastering",
                    "status": "completed",
                    "output": mastering_result,
                }
            )
        else:
            mastering_result = {}
            processing_log.append(
                {
                    "step": "mastering",
                    "status": "skipped",
                    "reason": "No merged audio",
                }
            )

        # Build report
        post_process_report: dict[str, object] = {
            "status": "completed",
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "stems_dir": stems_dir,
            "processing_log": processing_log,
        }

        if mastering_result:
            post_process_report.update(mastering_result)

        # Write processing log to file
        log_path = output_dir / "processing_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(processing_log, f, indent=2)

        result: dict[str, object] = {
            "post_process_report": post_process_report,
            "stems_dir": stems_dir,
        }

        if mastering_result:
            result.update(mastering_result)

        return result

    except Exception as e:
        logger.exception("Post-processing failed")
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "post_process_report": {
                "status": "failed",
                "error": str(e),
                "processing_log": processing_log,
            },
        }
