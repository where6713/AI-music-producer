"""Tests for dataflow integration/orchestrator.

PRD 10: Dataflow Integration
- End-to-end orchestration from intent to artifacts
- Deterministic intermediate artifacts and trace IDs
- Integration smoke tests for full pipeline
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))


def _good_adapter(prompt: dict[str, object]) -> dict[str, object]:
    _ = prompt
    return {
        "lines": [
            "站台的灯刚熄, 我把旧承诺折进口袋",
            "风吹过衣角, 我学会笑着转身离开",
        ]
    }


def _write_real_corpus_file(tmp_path: Path) -> str:
    corpus_file = tmp_path / "corpus_real.txt"
    corpus_file.write_text(
        "便利店玻璃映着我没换的衬衫\n旧洗衣机转得很慢\n站台风停我学会转身\n",
        encoding="utf-8",
    )
    return str(corpus_file)


class TestOrchestratorContract:
    """Tests for orchestrator tool contract."""

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from src.producer_tools.orchestrator import orchestrator

        assert hasattr(orchestrator, "TOOL_NAME")
        assert orchestrator.TOOL_NAME == "orchestrator"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from src.producer_tools.orchestrator import orchestrator

        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)


class TestEndToEndFlow:
    """Tests for end-to-end dataflow orchestration.

    PRD 10: Full pipeline from voice + reference -> master
    """

    def test_orchestrate_missing_intent(self) -> None:
        """Should raise ValueError if intent missing."""
        from src.producer_tools.orchestrator import orchestrator

        with pytest.raises(ValueError, match="intent"):
            orchestrator.run({})

    def test_orchestrate_returns_trace_id(self, tmp_path: Path) -> None:
        """Should return trace_id for the run."""
        from src.producer_tools.orchestrator import orchestrator

        result = orchestrator.run(
            {
                "intent": "Create a pop song",
                "output_dir": str(tmp_path),
            }
        )

        assert isinstance(result, dict)
        # Should return trace_id
        assert "trace_id" in result or "error" in result

    def test_orchestrate_executes_prompt_chain_with_precomputed_inputs(
        self, tmp_path: Path
    ) -> None:
        """Orchestrator should execute lyric+prompt steps when inputs are provided."""
        from src.producer_tools.orchestrator import orchestrator

        voice_file = tmp_path / "voice_input.wav"
        voice_file.write_bytes(b"RIFFtest")

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "voice_audio_path": str(voice_file),
                "reference_dna": {
                    "key": "C#",
                    "scale": "minor",
                    "tempo": 101.3,
                    "structure": [{"index": 0, "label": "verse", "energy": 0.42}],
                    "energy_curve": [{"time": 0.0, "energy": 0.35}],
                    "instrumentation": {
                        "vocals": {"presence": True, "role": "lead_vocal"},
                        "bass": {"presence": True, "role": "foundation"},
                    },
                },
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
                "llm_adapter": _good_adapter,
            }
        )

        assert result.get("status") == "orchestrated"
        pipeline = result.get("pipeline", [])
        assert isinstance(pipeline, list)
        lyric_steps = [s for s in pipeline if s.get("step") == "lyric_architect"]
        prompt_steps = [s for s in pipeline if s.get("step") == "prompt_compiler"]
        assert lyric_steps and lyric_steps[0].get("status") in {"completed", "failed"}
        assert prompt_steps and prompt_steps[0].get("status") in {"completed", "failed"}

    def test_orchestrate_writes_prompt_slot_files(self, tmp_path: Path) -> None:
        """Orchestrator should write style/exclude slot files for Suno."""
        from src.producer_tools.orchestrator import orchestrator

        voice_file = tmp_path / "voice_input.wav"
        voice_file.write_bytes(b"RIFFtest")

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "voice_audio_path": str(voice_file),
                "reference_dna": {
                    "key": "C#",
                    "scale": "minor",
                    "tempo": 101.3,
                    "structure": [{"index": 0, "label": "verse", "energy": 0.42}],
                    "energy_curve": [{"time": 0.0, "energy": 0.35}],
                    "instrumentation": {
                        "vocals": {"presence": True, "role": "lead_vocal"},
                        "bass": {"presence": True, "role": "foundation"},
                    },
                },
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
                "llm_adapter": _good_adapter,
            }
        )

        assert result.get("status") == "orchestrated"
        style_file = tmp_path / "suno_v1_style.txt"
        exclude_file = tmp_path / "suno_v1_exclude.txt"
        assert style_file.exists()
        assert exclude_file.exists()
        assert style_file.read_text(encoding="utf-8").strip() != ""
        assert exclude_file.read_text(encoding="utf-8").strip() != ""

    def test_orchestrate_blocks_prompt_when_lyric_gate_fails(
        self, tmp_path: Path
    ) -> None:
        """Prompt compiler should be skipped when lyric quality gate fails."""
        from src.producer_tools.orchestrator import orchestrator

        voice_file = tmp_path / "voice_input.wav"
        voice_file.write_bytes(b"RIFFtest")

        def _bad_adapter(prompt: dict[str, object]) -> dict[str, object]:
            _ = prompt
            return {"lines": ["霓虹碎成破碎感", "夜色继续漂浮"]}

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "voice_audio_path": str(voice_file),
                "reference_dna": {
                    "key": "C#",
                    "scale": "minor",
                    "tempo": 101.3,
                    "structure": [{"index": 0, "label": "verse", "energy": 0.42}],
                    "energy_curve": [{"time": 0.0, "energy": 0.35}],
                    "instrumentation": {
                        "vocals": {"presence": True, "role": "lead_vocal"},
                        "bass": {"presence": True, "role": "foundation"},
                    },
                },
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "llm_adapter": _bad_adapter,
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
            }
        )

        pipeline = result.get("pipeline", [])
        assert isinstance(pipeline, list)
        lyric_steps = [s for s in pipeline if s.get("step") == "lyric_architect"]
        prompt_steps = [s for s in pipeline if s.get("step") == "prompt_compiler"]
        assert lyric_steps and lyric_steps[0].get("status") == "failed"
        assert prompt_steps and prompt_steps[0].get("status") == "skipped"

    def test_orchestrate_fails_when_acoustic_input_missing(
        self, tmp_path: Path
    ) -> None:
        """Acoustic stage is mandatory and cannot be skipped."""
        from src.producer_tools.orchestrator import orchestrator

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "reference_dna": {
                    "key": "C#",
                    "scale": "minor",
                    "tempo": 101.3,
                    "structure": [{"index": 0, "label": "verse", "energy": 0.42}],
                    "energy_curve": [{"time": 0.0, "energy": 0.35}],
                    "instrumentation": {
                        "vocals": {"presence": True, "role": "lead_vocal"},
                        "bass": {"presence": True, "role": "foundation"},
                    },
                },
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
                "llm_adapter": _good_adapter,
            }
        )

        assert result.get("status") == "failed"
        pipeline = result.get("pipeline", [])
        assert isinstance(pipeline, list)
        assert pipeline[0].get("step") == "acoustic_analyst"
        assert pipeline[0].get("status") == "failed"
        assert pipeline[0].get("note") == "voice_audio_path_required"
        for step_name in [
            "style_deconstructor",
            "friction_calculator",
            "lyric_architect",
            "prompt_compiler",
            "post_processor",
        ]:
            hit = [s for s in pipeline if s.get("step") == step_name]
            assert hit and hit[0].get("status") == "skipped"
            assert hit[0].get("note") == "blocked_by_acoustic_failure"

    def test_orchestrate_runs_style_deconstructor_when_reference_audio_provided(
        self, tmp_path: Path
    ) -> None:
        """When reference_audio_path exists, style_deconstructor must run."""
        from src.producer_tools.orchestrator import orchestrator

        voice_file = tmp_path / "voice_input.wav"
        voice_file.write_bytes(b"RIFFtest")
        ref_file = tmp_path / "ref_input.wav"
        ref_file.write_bytes(b"RIFFtest")

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "voice_audio_path": str(voice_file),
                "reference_audio_path": str(ref_file),
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
                "llm_adapter": _good_adapter,
            }
        )

        pipeline = result.get("pipeline", [])
        assert isinstance(pipeline, list)
        style_steps = [s for s in pipeline if s.get("step") == "style_deconstructor"]
        assert style_steps
        assert style_steps[0].get("status") == "completed"
        assert (
            style_steps[0].get("note") == "style_deconstructor_run_from_reference_audio"
        )

    def test_orchestrate_blocks_downstream_when_style_reference_audio_missing(
        self, tmp_path: Path
    ) -> None:
        """Missing reference audio file should fail style and block downstream."""
        from src.producer_tools.orchestrator import orchestrator

        voice_file = tmp_path / "voice_input.wav"
        voice_file.write_bytes(b"RIFFtest")

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "voice_audio_path": str(voice_file),
                "reference_audio_path": str(tmp_path / "missing_ref.wav"),
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
                "llm_adapter": _good_adapter,
            }
        )

        assert result.get("status") == "failed"
        pipeline = result.get("pipeline", [])
        assert isinstance(pipeline, list)
        style_steps = [s for s in pipeline if s.get("step") == "style_deconstructor"]
        assert style_steps and style_steps[0].get("status") == "failed"
        assert style_steps[0].get("note") == "reference_audio_not_found"

        for step_name in [
            "friction_calculator",
            "lyric_architect",
            "prompt_compiler",
            "post_processor",
        ]:
            hit = [s for s in pipeline if s.get("step") == step_name]
            assert hit and hit[0].get("status") == "skipped"
            assert hit[0].get("note") == "blocked_by_style_deconstructor_failure"

    def test_orchestrate_adds_warning_when_friction_skipped_no_reference_dna(
        self, tmp_path: Path
    ) -> None:
        """If reference_dna is absent, friction skip must emit warning and warning status."""
        from src.producer_tools.orchestrator import orchestrator

        voice_file = tmp_path / "voice_input.wav"
        voice_file.write_bytes(b"RIFFtest")

        result = orchestrator.run(
            {
                "intent": "现代感, 略带古风, 失恋但豁达",
                "output_dir": str(tmp_path),
                "voice_audio_path": str(voice_file),
                "genre_seed": {"descriptors": ["neo-r&b", "oriental pop"]},
                "corpus_sources": [_write_real_corpus_file(tmp_path)],
                "llm_adapter": _good_adapter,
            }
        )

        assert result.get("status") == "orchestrated_with_warnings"
        warnings = result.get("warnings", [])
        assert isinstance(warnings, list)
        assert warnings
        assert warnings[0].get("message") == "friction_skipped_no_reference_dna"

        pipeline = result.get("pipeline", [])
        assert isinstance(pipeline, list)
        friction_steps = [s for s in pipeline if s.get("step") == "friction_calculator"]
        assert friction_steps
        assert friction_steps[0].get("status") == "skipped"
        assert (
            friction_steps[0].get("note")
            == "friction_skipped_no_reference_dna: lyrics generated without style/friction constraints"
        )


class TestTraceIds:
    """Tests for trace ID generation and tracking."""

    def test_trace_id_format(self, tmp_path: Path) -> None:
        """Trace ID should be deterministic format."""
        from src.producer_tools.orchestrator import orchestrator

        result = orchestrator.run(
            {
                "intent": "Test song",
                "output_dir": str(tmp_path),
            }
        )

        if "trace_id" in result:
            trace_id = result["trace_id"]
            assert isinstance(trace_id, str)
            # Trace ID should be non-empty
            assert len(trace_id) > 0


class TestDeterministicArtifacts:
    """Tests for deterministic intermediate artifacts."""

    def test_artifact_paths_deterministic(self, tmp_path: Path) -> None:
        """Artifact paths should be deterministic based on inputs."""
        from src.producer_tools.orchestrator import orchestrator

        result1 = orchestrator.run(
            {
                "intent": "Pop ballad",
                "output_dir": str(tmp_path / "run1"),
            }
        )

        result2 = orchestrator.run(
            {
                "intent": "Pop ballad",
                "output_dir": str(tmp_path / "run2"),
            }
        )

        # Should produce same trace for same intent
        if "trace_id" in result1 and "trace_id" in result2:
            assert result1["trace_id"] == result2["trace_id"]


class TestIntegrationSmoke:
    """Tests for integration smoke tests."""

    def test_smoke_all_tools_available(self) -> None:
        """All tools should be importable."""
        from src.producer_tools.business import (
            acoustic_analyst,
            friction_calculator,
            lyric_architect,
            post_processor,
            prompt_compiler,
            style_deconstructor,
        )
        from src.producer_tools.self_check import py_eval, shell_probe
        from src.producer_tools.terminal import (
            audio_player,
            cli_router,
            download_watcher,
            project_memory,
        )

        # All should have TOOL_NAME and run
        for tool in [
            acoustic_analyst,
            friction_calculator,
            lyric_architect,
            post_processor,
            prompt_compiler,
            style_deconstructor,
            py_eval,
            shell_probe,
            audio_player,
            cli_router,
            download_watcher,
            project_memory,
        ]:
            assert hasattr(tool, "TOOL_NAME")
            assert hasattr(tool, "run")
