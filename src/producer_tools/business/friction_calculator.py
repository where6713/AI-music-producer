"""Skeleton for friction_calculator tool."""

from __future__ import annotations

import json
import math
from pathlib import Path

from ..contracts import ToolPayload, ToolResult

TOOL_NAME = "friction_calculator"


def calculate_hard_constraints(
    voice_profile: dict[str, object] | None,
) -> dict[str, object]:
    """Calculate hard-constraint compatibility score.

    Returns:
        dict with ok, hard_constraints{score}, conflicts
    """
    if voice_profile is None:
        return {
            "ok": False,
            "error": "voice_profile_required",
            "hard_constraints": None,
            "conflicts": [],
        }

    try:
        f0_dict = voice_profile.get("f0") if isinstance(voice_profile, dict) else None
        if not isinstance(f0_dict, dict):
            f0_dict = {}
        median_freq = (
            float(f0_dict.get("median", 220.0)) if isinstance(f0_dict, dict) else 220.0
        )
        p10_freq = (
            float(f0_dict.get("p10", 180.0)) if isinstance(f0_dict, dict) else 180.0
        )
        p90_freq = (
            float(f0_dict.get("p90", 280.0)) if isinstance(f0_dict, dict) else 280.0
        )

        # Voice range in semitones
        if median_freq > 0:
            voice_range_semitones = 12.0 * (p90_freq - p10_freq) / median_freq
        else:
            voice_range_semitones = 0.0

        # Score: higher range = better adaptability
        if voice_range_semitones < 12:
            score = 50.0
        elif voice_range_semitones < 24:
            score = 75.0
        else:
            score = 100.0

        return {
            "ok": True,
            "hard_constraints": {
                "score": score,
                "voice_range_semitones": round(voice_range_semitones, 1),
            },
            "conflicts": [],
        }
    except (ValueError, TypeError):
        return {
            "ok": False,
            "error": "invalid_voice_profile",
            "hard_constraints": None,
            "conflicts": [],
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns value in [-1, 1]. Returns 0.0 for zero-norm vectors.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def calculate_timbre_fit(
    voice_profile: dict[str, object],
    reference_dna: dict[str, object],
) -> dict[str, object]:
    """Calculate timbre fit score via CLAP embedding cosine similarity.

    PRD 5.3 layer 2: CLAP embedding cosine similarity -> 0-100 score.

    Args:
        voice_profile: dict with 'embedding_clap' (list[float], 512-dim).
        reference_dna: dict with 'embedding_clap' (list[float], 512-dim).

    Returns:
        dict with ok, timbre_fit{score, similarity}, or ok=False on error.
    """
    vp_emb = (
        voice_profile.get("embedding_clap") if isinstance(voice_profile, dict) else None
    )
    rd_emb = (
        reference_dna.get("embedding_clap") if isinstance(reference_dna, dict) else None
    )

    if not isinstance(vp_emb, list) or len(vp_emb) == 0:
        return {
            "ok": False,
            "error": "voice_profile_missing_embedding_clap",
            "timbre_fit": None,
        }
    if not isinstance(rd_emb, list) or len(rd_emb) == 0:
        return {
            "ok": False,
            "error": "reference_dna_missing_embedding_clap",
            "timbre_fit": None,
        }

    try:
        vec_a = [float(v) for v in vp_emb]
        vec_b = [float(v) for v in rd_emb]
    except (ValueError, TypeError):
        return {
            "ok": False,
            "error": "invalid_embedding_values",
            "timbre_fit": None,
        }

    similarity = _cosine_similarity(vec_a, vec_b)

    # Map cosine similarity [-1, 1] to score [0, 100]
    # similarity=1 -> 100, similarity=0 -> 50, similarity=-1 -> 0
    score = (similarity + 1.0) * 50.0
    score = max(0.0, min(100.0, score))

    return {
        "ok": True,
        "timbre_fit": {
            "score": round(score, 2),
            "similarity": round(similarity, 4),
        },
    }


def generate_verdict(
    hard_constraints_score: float,
    timbre_fit_score: float,
) -> dict[str, object]:
    """Generate verdict from two-tier scores.

    PRD 5.3: overall_friction_index (0-100, lower=better),
    verdict: accept | adjust | reject.

    Args:
        hard_constraints_score: 0-100 from layer 1.
        timbre_fit_score: 0-100 from layer 2.

    Returns:
        dict with overall_friction_index, verdict, conflicts.
    """
    # Weighted: hard_constraints 60%, timbre_fit 40%
    compatibility = hard_constraints_score * 0.6 + timbre_fit_score * 0.4
    friction_index = round(100.0 - compatibility, 2)
    friction_index = max(0.0, min(100.0, friction_index))

    conflicts: list[dict[str, object]] = []
    if hard_constraints_score < 50:
        conflicts.append(
            {"layer": "hard_constraints", "issue": "low_voice_range_score"}
        )
    if timbre_fit_score < 40:
        conflicts.append({"layer": "timbre_fit", "issue": "low_timbre_similarity"})

    if friction_index < 20:
        verdict = "accept"
    elif friction_index < 60:
        verdict = "adjust"
    else:
        verdict = "reject"

    return {
        "overall_friction_index": friction_index,
        "verdict": verdict,
        "conflicts": conflicts,
    }


def generate_adjustments(
    voice_profile: dict[str, object],
    reference_dna: dict[str, object],
) -> dict[str, object]:
    """Generate recommended adjustments based on voice vs reference.

    PRD 5.3: recommended_adjustments with transpose_semitones,
    target_key, tempo_bpm, vocal_style_tags,
    instrumentation_emphasis/deemphasis, structure_modifications.

    Args:
        voice_profile: dict with f0 data.
        reference_dna: dict with tempo, key, scale.

    Returns:
        dict with adjustment recommendations.
    """
    # Extract voice f0
    f0_dict = voice_profile.get("f0") if isinstance(voice_profile, dict) else None
    if isinstance(f0_dict, dict):
        median_freq = float(f0_dict.get("median", 220.0))
    else:
        median_freq = 220.0

    # Extract reference tempo/key
    ref_tempo = 120.0
    if isinstance(reference_dna, dict):
        tempo_val = reference_dna.get("tempo", 120.0)
        if isinstance(tempo_val, (int, float)):
            ref_tempo = float(tempo_val)
    ref_key = (
        str(reference_dna.get("key", "C")) if isinstance(reference_dna, dict) else "C"
    )

    # Transpose suggestion: if voice is high, suggest down; low, suggest up
    if median_freq > 300:
        transpose_semitones = -2
    elif median_freq < 180:
        transpose_semitones = 2
    else:
        transpose_semitones = 0

    # Vocal style tags based on voice characteristics
    style_tags: list[str] = []
    if median_freq > 250:
        style_tags.append("head_voice")
    if median_freq < 200:
        style_tags.append("chest_voice")

    return {
        "transpose_semitones": transpose_semitones,
        "target_key": ref_key,
        "tempo_bpm": ref_tempo,
        "vocal_style_tags": style_tags,
        "instrumentation_emphasis": [],
        "instrumentation_deemphasis": [],
        "structure_modifications": [],
    }


def generate_friction_report(
    voice_profile: dict[str, object],
    reference_dna: dict[str, object],
) -> dict[str, object]:
    """Generate full friction report combining all three tiers.

    PRD 5.3: overall friction report with verdict, conflicts,
    recommended_adjustments, cultural_notes.

    Args:
        voice_profile: dict with f0, embedding_clap, etc.
        reference_dna: dict with tempo, key, embedding_clap, etc.

    Returns:
        Full friction_report dict.
    """
    # Tier 1: hard constraints
    hc_result = calculate_hard_constraints(voice_profile)
    if not hc_result.get("ok"):
        hc_score = 0.0
    else:
        hc_raw = hc_result.get("hard_constraints")
        hc_score = float(hc_raw.get("score", 0.0)) if isinstance(hc_raw, dict) else 0.0

    # Tier 2: timbre fit
    tf_result = calculate_timbre_fit(voice_profile, reference_dna)
    if not tf_result.get("ok"):
        tf_score = 50.0  # neutral default when embeddings unavailable
    else:
        tf_raw = tf_result.get("timbre_fit")
        tf_score = (
            float(tf_raw.get("score", 50.0)) if isinstance(tf_raw, dict) else 50.0
        )

    # Generate verdict
    verdict_data = generate_verdict(hc_score, tf_score)

    # Generate adjustments
    adjustments = generate_adjustments(voice_profile, reference_dna)

    return {
        "ok": True,
        "overall_friction_index": verdict_data["overall_friction_index"],
        "verdict": verdict_data["verdict"],
        "conflicts": verdict_data["conflicts"],
        "recommended_adjustments": adjustments,
        "cultural_notes": [],
    }


def run(payload: ToolPayload) -> ToolResult:
    """Execute the friction_calculator tool.

    PRD 5.3: Three-tier waterfall friction analysis.

    Payload keys:
        voice_profile: dict with f0, embedding_clap, etc.
        reference_dna: dict with tempo, key, embedding_clap, etc.
        output_path: optional path to write friction_report.json.

    Returns:
        ToolResult with ok, friction_report, and optional output_path.
    """
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv(override=False)
    except Exception:
        pass

    voice_profile = payload.get("voice_profile")
    reference_dna = payload.get("reference_dna")

    if not isinstance(voice_profile, dict):
        return {
            "ok": False,
            "error": "voice_profile_required",
            "friction_report": None,
        }

    if not isinstance(reference_dna, dict):
        return {
            "ok": False,
            "error": "reference_dna_required",
            "friction_report": None,
        }

    # Generate full friction report
    report = generate_friction_report(voice_profile, reference_dna)

    # Handle optional output_path
    output_path_value = payload.get("output_path")
    if output_path_value and isinstance(output_path_value, (str, Path)):
        output_path = Path(output_path_value).expanduser().resolve()
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Prepare JSON-serializable report (remove 'ok' from internal report)
            json_report = {
                "overall_friction_index": report.get("overall_friction_index"),
                "verdict": report.get("verdict"),
                "conflicts": report.get("conflicts", []),
                "recommended_adjustments": report.get("recommended_adjustments", {}),
                "cultural_notes": report.get("cultural_notes", []),
            }
            _ = output_path.write_text(
                json.dumps(json_report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # Ignore write errors, still return the report

    return {
        "ok": True,
        "friction_report": report,
        "output_path": str(output_path_value) if output_path_value else "",
    }
