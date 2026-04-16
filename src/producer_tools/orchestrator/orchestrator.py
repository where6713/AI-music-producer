"""Orchestrator for end-to-end dataflow integration.

PRD 10: Dataflow Integration
- End-to-end orchestration from intent to artifacts
- Deterministic intermediate artifacts and trace IDs
- Integration smoke tests for full pipeline
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..business import (
    acoustic_analyst,
    friction_calculator,
    lyric_architect,
    prompt_compiler,
)
from ..contracts import ToolPayload, ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "orchestrator"

logger = logging.getLogger(__name__)


def _generate_trace_id(intent: str, seed: str = "") -> str:
    """Generate deterministic trace ID from intent.

    Args:
        intent: User intent string
        seed: Optional seed for variation

    Returns:
        Deterministic trace ID string
    """
    combined = f"{intent}:{seed}:{datetime.now().strftime('%Y%m%d')}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _validate_intent(payload: Mapping[str, object]) -> str:
    """Validate and return intent from payload.

    Args:
        payload: Tool payload containing intent

    Returns:
        Intent string

    Raises:
        ValueError: If intent is missing
    """
    intent = payload.get("intent")
    if not intent:
        raise ValueError("intent is required")
    if not isinstance(intent, str):
        raise ValueError("intent must be a string")
    return intent


def _get_output_dir(payload: Mapping[str, object]) -> Path:
    """Get output directory from payload.

    Args:
        payload: Tool payload containing output_dir

    Returns:
        Path to output directory
    """
    output_dir = payload.get("output_dir")
    if output_dir and isinstance(output_dir, str):
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path.cwd()


def _orchestrate_full_pipeline(
    intent: str,
    output_dir: Path,
    trace_id: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    """Orchestrate the full pipeline from intent to artifacts.

    Pipeline:
    1. acoustic_analyst -> voice_profile.json
    2. style_deconstructor -> reference_dna.json
    3. friction_calculator -> friction_report.json
    4. lyric_architect -> lyrics.json
    5. prompt_compiler -> suno_v1.txt / minimax_v1.txt
    6. post_processor -> master_24bit.wav

    Args:
        intent: User intent
        output_dir: Output directory
        trace_id: Trace ID for this run

    Returns:
        dict with pipeline results
    """
    results: dict[str, object] = {
        "trace_id": trace_id,
        "intent": intent,
        "pipeline": [],
    }

    pipeline: list[dict[str, str]] = []
    reference_dna_raw = payload.get("reference_dna", {})
    reference_dna: dict[str, object] = (
        reference_dna_raw if isinstance(reference_dna_raw, dict) else {}
    )
    voice_profile_raw = payload.get("voice_profile", {})
    voice_profile: dict[str, object] = (
        voice_profile_raw if isinstance(voice_profile_raw, dict) else {}
    )
    genre_seed_raw = payload.get("genre_seed", {})
    genre_seed: dict[str, object] = (
        genre_seed_raw if isinstance(genre_seed_raw, dict) else {}
    )
    require_real_corpus = bool(payload.get("require_real_corpus", True))

    # Step 1: Acoustic Analyst (MANDATORY)
    voice_audio_value = payload.get("voice_audio_path")
    if voice_audio_value is None:
        voice_audio_value = payload.get("audio_path")
    if voice_audio_value is None:
        voice_audio_value = payload.get("dry_vocal_path")

    voice_audio_path: Path | None = None
    if isinstance(voice_audio_value, Path):
        voice_audio_path = voice_audio_value.expanduser().resolve()
    elif isinstance(voice_audio_value, str) and voice_audio_value.strip():
        voice_audio_path = Path(voice_audio_value).expanduser().resolve()

    if (
        voice_audio_path is None
        or not voice_audio_path.exists()
        or not voice_audio_path.is_file()
    ):
        pipeline.append(
            {
                "step": "acoustic_analyst",
                "status": "failed",
                "note": "voice_audio_path_required",
            }
        )
        pipeline.extend(
            [
                {
                    "step": "style_deconstructor",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "friction_calculator",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "lyric_architect",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "prompt_compiler",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "post_processor",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
            ]
        )
        results["pipeline"] = pipeline
        results["status"] = "failed"
        results["message"] = "acoustic_analyst is mandatory and cannot be skipped"
        return results

    acoustic_result = acoustic_analyst.run(
        {
            "audio_path": str(voice_audio_path),
            "use_parselmouth": True,
            "voice_profile_path": str(output_dir / "voice_profile.json"),
        }
    )
    if not acoustic_result.get("ok"):
        pipeline.append(
            {
                "step": "acoustic_analyst",
                "status": "failed",
                "note": str(acoustic_result.get("error", "acoustic_failed")),
            }
        )
        pipeline.extend(
            [
                {
                    "step": "style_deconstructor",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "friction_calculator",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "lyric_architect",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "prompt_compiler",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
                {
                    "step": "post_processor",
                    "status": "skipped",
                    "note": "blocked_by_acoustic_failure",
                },
            ]
        )
        results["pipeline"] = pipeline
        results["status"] = "failed"
        results["message"] = "acoustic_analyst failed; downstream pipeline blocked"
        return results

    profile_val = acoustic_result.get("voice_profile", {})
    if isinstance(profile_val, dict):
        voice_profile = profile_val

    pipeline.append(
        {
            "step": "acoustic_analyst",
            "status": "completed",
            "note": "voice_profile generated",
        }
    )

    # Step 2: Style Deconstructor (or precomputed reference_dna)
    if reference_dna:
        pipeline.append(
            {
                "step": "style_deconstructor",
                "status": "completed",
                "note": "Using precomputed reference_dna",
            }
        )
    else:
        pipeline.append(
            {
                "step": "style_deconstructor",
                "status": "skipped",
                "note": "Requires reference audio input",
            }
        )

    # Step 3: Friction Calculator
    friction_report: dict[str, object] = {}
    if reference_dna:
        friction_result = friction_calculator.run(
            {
                "voice_profile": voice_profile,
                "reference_dna": reference_dna,
                "output_path": str(output_dir / "friction_report.json"),
            }
        )
        if friction_result.get("ok"):
            report_val = friction_result.get("friction_report", {})
            friction_report = report_val if isinstance(report_val, dict) else {}
            pipeline.append(
                {
                    "step": "friction_calculator",
                    "status": "completed",
                    "note": "friction_report generated",
                }
            )
        else:
            pipeline.append(
                {
                    "step": "friction_calculator",
                    "status": "failed",
                    "note": str(friction_result.get("error", "friction_failed")),
                }
            )
    else:
        pipeline.append(
            {
                "step": "friction_calculator",
                "status": "skipped",
                "note": "Requires voice_profile and reference_dna",
            }
        )

    # Step 4: Lyric Architect
    lyrics_data: dict[str, object] = {}
    lyric_result = lyric_architect.run(
        {
            "intent": intent,
            "reference_dna": reference_dna,
            "output_path": str(output_dir / "lyrics.json"),
            "use_llm": True,
            "llm_adapter": payload.get("llm_adapter"),
            "llm_api_key": payload.get("llm_api_key"),
            "llm_base_url": payload.get("llm_base_url"),
            "llm_model": payload.get("llm_model"),
            "structure_template": payload.get("structure_template"),
            "structure_template_path": payload.get("structure_template_path"),
            "corpus_registry_path": payload.get("corpus_registry_path"),
            "corpus_sources": payload.get("corpus_sources", []),
            "require_real_corpus": require_real_corpus,
        }
    )
    if lyric_result.get("ok"):
        lyrics_val = lyric_result.get("lyrics", {})
        lyrics_data = lyrics_val if isinstance(lyrics_val, dict) else {}
        pipeline.append(
            {
                "step": "lyric_architect",
                "status": "completed",
                "note": "lyrics generated",
            }
        )
    else:
        pipeline.append(
            {
                "step": "lyric_architect",
                "status": "failed",
                "note": str(lyric_result.get("error", "lyric_generation_failed")),
            }
        )

    # Step 5: Prompt Compiler
    if reference_dna and lyrics_data:
        compile_result = prompt_compiler.run(
            {
                "genre_seed": genre_seed,
                "reference_dna": reference_dna,
                "lyrics": lyrics_data,
                "voice_profile": voice_profile,
            }
        )
        if compile_result.get("ok"):
            try:
                (output_dir / "suno_v1.txt").write_text(
                    str(compile_result.get("style", ""))
                    + "\n\n"
                    + str(compile_result.get("lyrics", "")),
                    encoding="utf-8",
                )
                (output_dir / "suno_v1_style.txt").write_text(
                    str(compile_result.get("style", "")),
                    encoding="utf-8",
                )
                (output_dir / "suno_v1_exclude.txt").write_text(
                    str(compile_result.get("exclude", "")),
                    encoding="utf-8",
                )
                (output_dir / "minimax_v1.txt").write_text(
                    str(compile_result.get("style", ""))
                    + "\n\n"
                    + str(compile_result.get("lyrics", "")),
                    encoding="utf-8",
                )
                (output_dir / "compile_log.json").write_text(
                    json.dumps(
                        compile_result.get("compile_log", {}),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except OSError:
                pass
            pipeline.append(
                {
                    "step": "prompt_compiler",
                    "status": "completed",
                    "note": "prompt assets generated",
                }
            )
        else:
            pipeline.append(
                {
                    "step": "prompt_compiler",
                    "status": "failed",
                    "note": str(compile_result.get("error", "prompt_compile_failed")),
                }
            )
    else:
        pipeline.append(
            {
                "step": "prompt_compiler",
                "status": "skipped",
                "note": "Requires lyrics.json and reference_dna",
            }
        )

    # Step 6: Post Processor
    pipeline.append(
        {
            "step": "post_processor",
            "status": "skipped",
            "note": "Requires take audio input",
        }
    )

    results["pipeline"] = pipeline
    results["status"] = "orchestrated"
    results["message"] = f"Pipeline orchestrated with trace_id={trace_id}"

    return results


def run(payload: ToolPayload) -> ToolResult:
    """Execute the orchestrator tool.

    PRD 10: End-to-end dataflow orchestration from intent to artifacts.

    Args:
        payload: Must contain:
            - intent: User intent string

        Optional:
            - output_dir: Output directory (default: current directory)

    Returns:
        ToolResult containing:
            - trace_id: Deterministic trace ID for this run
            - pipeline: List of pipeline steps and their status
            - status: Overall pipeline status
    """
    intent = _validate_intent(payload)
    output_dir = _get_output_dir(payload)

    trace_id = _generate_trace_id(intent)

    try:
        results = _orchestrate_full_pipeline(intent, output_dir, trace_id, payload)

        # Save trace info to output directory
        trace_file = output_dir / f"trace_{trace_id}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return results

    except Exception as e:
        logger.exception("Orchestration failed")
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "trace_id": trace_id,
        }
