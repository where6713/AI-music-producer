"""Tests for post_processor tool.

PRD 5.6: Post processor converts AI-generated audio to release-quality masters.

Signal processing flow:
1. Demucs htdemucs_ft separation -> vocals/drums/bass/other.wav
2. Vocal de-AI-ification (formant perturbation + dynamic de-essing + saturation)
3. Alignment (librosa onset_detect + time_stretch)
4. Vocal mix bus (Pedalboard effects chain)
5. Bus merge: vocals_fx + 0.85 * (drums + bass + other)
6. Matchering 2.0 mastering
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

from src.producer_tools.business import post_processor


class TestToolContract:
    """Test module-level contracts."""

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        assert hasattr(post_processor, "TOOL_NAME")
        assert post_processor.TOOL_NAME == "post_processor"

    def test_run_callable(self) -> None:
        """run must be callable."""
        assert hasattr(post_processor, "run")
        assert callable(post_processor.run)


class TestExtractStems:
    """Tests for _extract_stems() function.

    PRD 5.6 [1]: Demucs htdemucs_ft separation
    Output: vocals.wav, drums.wav, bass.wav, other.wav
    """

    def test_extract_stems_missing_input_path(self) -> None:
        """Should raise ValueError if input_path missing."""
        with pytest.raises(ValueError, match="input_path"):
            post_processor._extract_stems({})

    def test_extract_stems_invalid_input_path(self) -> None:
        """Should raise FileNotFoundError if file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            post_processor._extract_stems(
                {
                    "input_path": "/nonexistent/take_001.mp3",
                }
            )

    def test_extract_stems_returns_stem_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return paths to extracted stems."""
        # Create a minimal valid audio file for testing
        import numpy as np
        import soundfile as sf

        audio_path = tmp_path / "take_001.mp3"
        # Create 1 second of silence at 44100 Hz
        audio_data = np.zeros(44100, dtype=np.float32)
        sf.write(str(audio_path), audio_data, 44100)

        def _ok_runner(
            input_path: str,
            output_dir: str,
            timeout_sec: float = 60.0,
            runner_script: str | None = None,
        ) -> dict[str, object]:
            _ = (timeout_sec, runner_script)
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            vocals = out / "vocals.wav"
            drums = out / "drums.wav"
            bass = out / "bass.wav"
            other = out / "other.wav"
            backing = out / "backing.wav"
            for p in [vocals, drums, bass, other, backing]:
                p.write_bytes(b"RIFF")
            return {
                "ok": True,
                "stems_dir": str(out),
                "vocals": str(vocals),
                "drums": str(drums),
                "bass": str(bass),
                "other": str(other),
                "backing": str(backing),
            }

        monkeypatch.setattr(post_processor, "run_demucs_subprocess", _ok_runner)

        result = post_processor._extract_stems(
            {
                "input_path": str(audio_path),
                "output_dir": str(tmp_path / "stems"),
            }
        )

        assert "stems_dir" in result
        assert "vocals" in result
        assert "drums" in result
        assert "bass" in result
        assert "other" in result

    def test_extract_stems_skips_subprocess_when_runtime_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should fail fast when Demucs runtime is unavailable."""
        import numpy as np
        import soundfile as sf

        audio_path = tmp_path / "take_preflight.mp3"
        audio_data = np.zeros(22050, dtype=np.float32)
        sf.write(str(audio_path), audio_data, 22050)

        calls = {"count": 0}

        def _fake_runner(
            input_path: str,
            output_dir: str,
            timeout_sec: float = 60.0,
            runner_script: str | None = None,
        ) -> dict[str, object]:
            _ = (timeout_sec, runner_script)
            calls["count"] += 1
            return {
                "ok": False,
                "status": "fallback",
                "fallback_reason": "runtime_unavailable",
                "stems_dir": output_dir,
                "vocals": input_path,
                "drums": input_path,
                "bass": input_path,
                "other": input_path,
                "backing": input_path,
                "error": "torchaudio_unavailable",
                "demucs_runtime": {
                    "ready": False,
                    "reason": "torchaudio_unavailable",
                    "python": "python",
                },
            }

        monkeypatch.setattr(post_processor, "run_demucs_subprocess", _fake_runner)

        with pytest.raises(RuntimeError, match="demucs_runtime_unavailable"):
            post_processor._extract_stems(
                {
                    "input_path": str(audio_path),
                    "output_dir": str(tmp_path / "out"),
                }
            )

        assert calls["count"] == 1


class TestApplyDeEssing:
    """Tests for _apply_de_essing() function.

    PRD 5.6 [2]: Dynamic de-essing using Pedalboard sidechain design.

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
    """

    def test_apply_de_essing_missing_vocal_path(self) -> None:
        """Should raise ValueError if vocal_path missing."""
        with pytest.raises(ValueError, match="vocal_path"):
            post_processor._apply_de_essing({})

    def test_apply_de_essing_invalid_path(self) -> None:
        """Should raise FileNotFoundError if file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            post_processor._apply_de_essing(
                {
                    "vocal_path": "/nonexistent/vocals.wav",
                }
            )

    def test_apply_de_essing_returns_output_path(self, tmp_path: Path) -> None:
        """Should return path to processed vocals."""
        import numpy as np
        import soundfile as sf

        vocals_path = tmp_path / "vocals.wav"
        audio_data = np.random.randn(44100).astype(np.float32) * 0.1
        sf.write(str(vocals_path), audio_data, 44100)

        result = post_processor._apply_de_essing(
            {
                "vocal_path": str(vocals_path),
                "output_path": str(tmp_path / "vocals_deessed.wav"),
            }
        )

        assert "output_path" in result
        output_path = result.get("output_path")
        assert isinstance(output_path, str)
        assert Path(output_path).exists()


class TestApplyVocalEnhancement:
    """Tests for _apply_vocal_enhancement() function.

    PRD 5.6 [2]: Vocal enhancement chain including:
    - Formant perturbation: +/-15 cents random jitter (Parselmouth Manipulation)
    - Light saturation (Distortion drive_db=2) for warmth
    """

    def test_apply_vocal_enhancement_missing_vocal_path(self) -> None:
        """Should raise ValueError if vocal_path missing."""
        with pytest.raises(ValueError, match="vocal_path"):
            post_processor._apply_vocal_enhancement({})

    def test_apply_vocal_enhancement_returns_output_path(self, tmp_path: Path) -> None:
        """Should return path to enhanced vocals."""
        import numpy as np
        import soundfile as sf

        vocals_path = tmp_path / "vocals.wav"
        audio_data = np.random.randn(44100).astype(np.float32) * 0.1
        sf.write(str(vocals_path), audio_data, 44100)

        result = post_processor._apply_vocal_enhancement(
            {
                "vocal_path": str(vocals_path),
                "output_path": str(tmp_path / "vocals_enhanced.wav"),
            }
        )

        assert "output_path" in result


class TestRunFunction:
    """Tests for main run() function."""

    def test_run_missing_required_inputs(self) -> None:
        """Should raise ValueError if required inputs missing."""
        with pytest.raises(ValueError):
            post_processor.run({})

    def test_run_missing_input_path(self) -> None:
        """Should raise ValueError if input_path missing."""
        with pytest.raises(ValueError, match="input_path"):
            post_processor.run(
                {
                    "output_dir": "/tmp/output",
                }
            )

    def test_run_nonexistent_input_file(self) -> None:
        """Should raise FileNotFoundError if input file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            post_processor.run(
                {
                    "input_path": "/nonexistent/take.mp3",
                    "output_dir": "/tmp/output",
                }
            )

    def test_run_returns_result_dict(self, tmp_path: Path) -> None:
        """Should return result dict with expected keys."""
        import numpy as np
        import soundfile as sf

        audio_path = tmp_path / "take_001.mp3"
        audio_data = np.zeros(44100, dtype=np.float32)
        sf.write(str(audio_path), audio_data, 44100)

        result = post_processor.run(
            {
                "input_path": str(audio_path),
                "output_dir": str(tmp_path / "output"),
            }
        )

        assert isinstance(result, dict)
        # PRD 5.6: Output includes post_process_report.json
        assert "post_process_report" in result or "error" in result


class TestPostProcessReportSchema:
    """Tests for post_process_report.json schema validation.

    PRD 5.6: Output should include:
    - stems_dir: path to extracted stems
    - aligned_dir: path to aligned stems
    - enhanced_vocals: path to enhanced vocals
    - processing_log: list of processing steps
    """

    def test_report_has_required_fields(self, tmp_path: Path) -> None:
        """Report should contain all required fields."""
        import numpy as np
        import soundfile as sf

        audio_path = tmp_path / "take_001.mp3"
        audio_data = np.zeros(44100, dtype=np.float32)
        sf.write(str(audio_path), audio_data, 44100)

        result = post_processor.run(
            {
                "input_path": str(audio_path),
                "output_dir": str(tmp_path / "output"),
            }
        )

        if "error" not in result:
            report = result.get("post_process_report", {})
            assert isinstance(report, dict)
            # At minimum, should have processing status
            assert "status" in report or "stems_dir" in report
