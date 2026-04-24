from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from src.claude_client import generate_lyric_payload
from src.compile import StructuralIncompleteError, write_outputs, write_trace_and_audit
from src.lint import lint_payload
from src.profile_router import resolve_active_profile
from src.retriever import InsufficientQualityFewShotError
from src.schemas import LyricPayload, UserInput


app = typer.Typer(help="Lyric Craftsman CLI (PRD v2.0)")

STRUCTURAL_REVISE_PROMPT = "下游要求 V/C/V/C/Bridge/C 中必须有 Verse 与 Chorus 各 >=1 段，每段 >=5 行"


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_profile_vote_from_source_ids(source_ids: list[str]) -> str:
    modern_hits = sum(1 for x in source_ids if x.startswith("lyric-modern-"))
    classical_hits = sum(1 for x in source_ids if x.startswith("poem-"))
    if modern_hits >= classical_hits and modern_hits > 0:
        return "urban_introspective"
    if classical_hits > 0:
        return "classical_restraint"
    return ""


def _infer_profile_confidence_from_source_ids(source_ids: list[str], profile_vote: str) -> float:
    if not source_ids or not profile_vote:
        return 0.0
    total = len(source_ids)
    if profile_vote == "urban_introspective":
        hits = sum(1 for x in source_ids if x.startswith("lyric-modern-"))
        return hits / max(total, 1)
    if profile_vote == "classical_restraint":
        hits = sum(1 for x in source_ids if x.startswith("poem-"))
        return hits / max(total, 1)
    return 0.0


def _build_targeted_revise_prompt(payload: dict[str, Any], lint_report: dict[str, Any]) -> str:
    return (
        "Targeted revise only for failing lines. Keep unchanged lines untouched.\n"
        f"Failed rules: {lint_report.get('failed_rules', [])}\n"
        f"Violations: {lint_report.get('violations', [])}\n"
        f"Current payload: {payload}"
    )


def _score_variants(payload: LyricPayload, *, trace: dict[str, Any] | None = None) -> tuple[LyricPayload, dict[str, Any]]:
    scored: list[tuple[str, bool, int, int, int]] = []
    dead_variants: list[str] = []
    for variant in payload.variants:
        probe = payload.model_copy(deep=True)
        probe.lyrics_by_section = variant.lyrics_by_section
        report = lint_payload(probe, trace=trace)
        passed_rules = 13 - len(report.get("failed_rules", []))
        variant.lint_result.passed_rules = passed_rules
        variant.lint_result.failed_rules = list(report.get("failed_rules", []))
        is_dead = bool(report.get("is_dead", False))
        if is_dead:
            dead_variants.append(variant.variant_id)
        penalty_score = int(report.get("penalty_score", 0) or 0)
        failed_count = len(report.get("failed_rules", []))
        scored.append((variant.variant_id, is_dead, penalty_score, passed_rules, failed_count))

    scored.sort(key=lambda x: (x[1], x[2], x[4], x[0]))
    ranking = {variant_id: idx for idx, (variant_id, _, _, _, _) in enumerate(scored, start=1)}
    for variant in payload.variants:
        variant.lint_result.rank = ranking.get(variant.variant_id, 99)

    all_dead = len(dead_variants) == len(payload.variants) if payload.variants else True
    chosen_variant_id = ""
    if not all_dead:
        for variant_id, is_dead, _, _, _ in scored:
            if not is_dead:
                chosen_variant_id = variant_id
                break

    if chosen_variant_id:
        payload.chosen_variant_id = chosen_variant_id
        for variant in payload.variants:
            if variant.variant_id == chosen_variant_id:
                payload.lyrics_by_section = variant.lyrics_by_section
                break

    ranking_view = [(variant_id, passed_rules, rank) for rank, (variant_id, _, _, passed_rules, _) in enumerate(scored, start=1)]
    return payload, {
        "ranking": ranking_view,
        "chosen_variant_id": chosen_variant_id,
        "all_dead": all_dead,
        "dead_variants": dead_variants,
    }


def _sync_chosen_variant(payload: LyricPayload) -> None:
    for variant in payload.variants:
        if variant.variant_id == payload.chosen_variant_id:
            variant.lyrics_by_section = payload.lyrics_by_section
            return


def _apply_retrieval_profile_decision(trace: dict[str, Any]) -> None:
    profile_vote = str(trace.get("retrieval_profile_vote", "")).strip()
    vote_confidence = _safe_float(trace.get("retrieval_vote_confidence", 0.0), default=0.0)
    explicit_active_profile = str(trace.get("active_profile", "")).strip()
    source_ids_raw = trace.get("few_shot_source_ids", [])
    source_ids = [str(x) for x in source_ids_raw] if isinstance(source_ids_raw, list) else []
    source_stage = str(trace.get("retrieval_profile_source", "initial")).strip() or "initial"
    profile_source = str(trace.get("profile_source", "")).strip()
    raw_vote_counts = trace.get("retrieval_profile_vote_counts", {})
    vote_counts = raw_vote_counts if isinstance(raw_vote_counts, dict) else {}

    if explicit_active_profile:
        if not profile_vote:
            profile_vote = explicit_active_profile
        if vote_confidence < (2 / 3):
            vote_confidence = 1.0
        trace["retrieval_profile_decision"] = {
            "profile_vote": profile_vote,
            "vote_confidence": vote_confidence,
            "active_profile": explicit_active_profile,
            "decision_reason": "activated",
            "source_stage": source_stage,
            "source_ids": source_ids,
            "source": profile_source,
            "profile_vote_counts": vote_counts,
        }
        return

    if not profile_vote:
        profile_vote = _infer_profile_vote_from_source_ids(source_ids)
        vote_confidence = _infer_profile_confidence_from_source_ids(source_ids, profile_vote)

    has_vote = bool(profile_vote)
    confidence_ok = vote_confidence >= (2 / 3)
    active_profile = profile_vote if (has_vote and confidence_ok) else ""
    if active_profile:
        decision_reason = "activated"
    elif not has_vote:
        decision_reason = "no_profile_vote"
    else:
        decision_reason = "insufficient_confidence"
    trace["retrieval_profile_decision"] = {
        "profile_vote": profile_vote,
        "vote_confidence": vote_confidence,
        "active_profile": active_profile,
        "decision_reason": decision_reason,
        "source_stage": source_stage,
        "source_ids": source_ids,
        "source": profile_source,
        "profile_vote_counts": vote_counts,
    }


def _merge_revise_trace_metadata(trace: dict[str, Any], revise_trace: dict[str, Any]) -> None:
    trace.setdefault("retrieval_profile_source", "initial")
    updated = False
    revise_profile_vote = str(revise_trace.get("retrieval_profile_vote", "")).strip()
    if revise_profile_vote:
        trace["retrieval_profile_vote"] = revise_profile_vote
        updated = True

    if "retrieval_vote_confidence" in revise_trace:
        trace["retrieval_vote_confidence"] = _safe_float(
            revise_trace.get("retrieval_vote_confidence", trace.get("retrieval_vote_confidence", 0.0)),
            default=_safe_float(trace.get("retrieval_vote_confidence", 0.0), default=0.0),
        )
        updated = True

    revise_source_ids_raw = revise_trace.get("few_shot_source_ids", [])
    revise_source_ids = [str(x) for x in revise_source_ids_raw] if isinstance(revise_source_ids_raw, list) else []
    if revise_source_ids:
        trace["few_shot_source_ids"] = revise_source_ids
        updated = True

    revise_vote_counts = revise_trace.get("retrieval_profile_vote_counts", {})
    if isinstance(revise_vote_counts, dict) and revise_vote_counts:
        trace["retrieval_profile_vote_counts"] = {str(k): int(v) for k, v in revise_vote_counts.items()}
        updated = True

    if updated:
        trace["retrieval_profile_source"] = "revise"


def _write_rejected_trace(out_dir: Path, trace: dict[str, Any]) -> None:
    write_trace_and_audit(out_dir, trace)


def _append_profile_routing_warnings(trace: dict[str, Any]) -> None:
    warnings = trace.get("profile_routing_warnings", [])
    if not isinstance(warnings, list):
        warnings = []

    profile_source = str(trace.get("profile_source", "")).strip()
    active_profile = str(trace.get("active_profile", "")).strip()
    vote_confidence = _safe_float(
        trace.get("profile_vote_confidence", trace.get("retrieval_vote_confidence", 0.0)),
        default=0.0,
    )
    retrieval_vote = str(trace.get("retrieval_profile_vote", "")).strip()
    low_confidence_route = profile_source == "corpus_vote" or (
        active_profile and retrieval_vote == active_profile
    )
    if low_confidence_route and active_profile and vote_confidence < 0.67:
        warning = (
            f"profile_routing_low_confidence profile={active_profile} "
            f"source={profile_source or 'unknown'} vote_confidence={vote_confidence:.2f}"
        )
        if warning not in warnings:
            warnings.append(warning)

    if warnings:
        trace["profile_routing_warnings"] = warnings


def _fail_quality_floor(target_dir: Path, trace: dict[str, Any], *, dry_run: bool) -> None:
    trace["run_status"] = "QUALITY_FLOOR_FAILED"
    if dry_run:
        typer.echo("dry-run complete")
        typer.echo("run_status=QUALITY_FLOOR_FAILED")
        raise typer.Exit(code=2)
    _write_rejected_trace(target_dir, trace)
    raise typer.Exit(code=2)


def _fail_generation_error(
    target_dir: Path,
    *,
    stage: str,
    exc: Exception,
    dry_run: bool,
) -> None:
    trace: dict[str, Any] = {
        "run_status": "REJECTED",
        "error_stage": stage,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }
    if dry_run:
        typer.echo("dry-run complete")
        typer.echo("run_status=REJECTED generation error")
        raise typer.Exit(code=2)
    write_trace_and_audit(target_dir, trace)
    raise typer.Exit(code=2)


@app.command("produce")
def produce(
    raw_intent: str = typer.Argument(...),
    genre: str = typer.Option("", "--genre"),
    mood: str = typer.Option("", "--mood"),
    vocal: str = typer.Option("any", "--vocal"),
    profile: str = typer.Option("", "--profile"),
    lang: str = typer.Option("zh-CN", "--lang"),
    out_dir: str = typer.Option("out", "--out-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    repo_root = Path.cwd()
    target_dir = Path(out_dir)

    user_input = UserInput(
        raw_intent=raw_intent,
        language=lang,
        genre_hint=genre,
        mood_hint=mood,
        vocal_gender_hint=vocal,
        profile_override=profile,
    )

    try:
        payload, trace = generate_lyric_payload(user_input, repo_root=repo_root)
    except InsufficientQualityFewShotError as exc:
        _fail_generation_error(target_dir, stage="few_shot_quality_gate", exc=exc, dry_run=dry_run)
    except Exception as exc:
        _fail_generation_error(target_dir, stage="initial_generation", exc=exc, dry_run=dry_run)
    trace.setdefault("retrieval_profile_source", "initial")
    active_profile, profile_source, profile_vote_confidence = resolve_active_profile(
        user_input,
        repo_root=repo_root,
        retrieval_vote=str(trace.get("retrieval_profile_vote", "")),
        vote_confidence=_safe_float(trace.get("retrieval_vote_confidence", 0.0), default=0.0),
    )

    trace["active_profile"] = active_profile
    trace["profile_source"] = profile_source
    if profile_vote_confidence is not None:
        trace["profile_vote_confidence"] = profile_vote_confidence
    _append_profile_routing_warnings(trace)
    payload, variant_rank = _score_variants(payload, trace=trace)
    lint_report = lint_payload(payload, trace=trace)

    llm_calls = 1
    warning_report = ""
    revise_evidence: dict[str, Any] = {}
    craft_score = float(lint_report.get("craft_score", 0.0) or 0.0)
    needs_quality_revise = craft_score < 0.85
    should_revise = bool(variant_rank.get("all_dead", False)) or (not lint_report["pass"]) or needs_quality_revise
    if should_revise:
        targeted_prompt = _build_targeted_revise_prompt(
            payload.model_dump(), lint_report
        )
        try:
            revised_payload, revise_trace = generate_lyric_payload(
                user_input,
                repo_root=repo_root,
                targeted_revise_prompt=targeted_prompt,
            )
        except InsufficientQualityFewShotError as exc:
            _fail_generation_error(target_dir, stage="few_shot_quality_gate", exc=exc, dry_run=dry_run)
        except Exception as exc:
            _fail_generation_error(target_dir, stage="targeted_revise_generation", exc=exc, dry_run=dry_run)
        revised_payload, revised_rank = _score_variants(revised_payload, trace=trace)
        revised_lint = lint_payload(revised_payload, trace=trace)
        payload = revised_payload
        lint_report = revised_lint
        llm_calls = 2
        usage_prev = trace.get("usage", {})
        usage_next = revise_trace.get("usage", {})
        trace["usage"] = {
            "input_tokens": int(usage_prev.get("input_tokens", 0)) + int(usage_next.get("input_tokens", 0)),
            "output_tokens": int(usage_prev.get("output_tokens", 0)) + int(usage_next.get("output_tokens", 0)),
            "total_tokens": int(usage_prev.get("total_tokens", 0)) + int(usage_next.get("total_tokens", 0)),
        }
        _merge_revise_trace_metadata(trace, revise_trace)
        trace["revise_trace"] = revise_trace
        revise_evidence = {
            "targeted_revise_prompt": targeted_prompt,
            "initial_failed_rules": variant_rank,
            "revised_failed_rules": revised_rank,
            "revised_lint_report": revised_lint,
        }
        variant_rank = revised_rank

        if bool(revised_rank.get("all_dead", False)):
            lint_report = dict(revised_lint)
            lint_report["all_dead_run_status"] = "REJECTED"
            trace["variant_rank"] = variant_rank
            trace["lint_report"] = lint_report
            trace["llm_calls"] = llm_calls
            trace["max_llm_calls_per_run"] = 2
            if revise_evidence:
                trace["revise_evidence"] = revise_evidence
            _apply_retrieval_profile_decision(trace)
            trace["run_status"] = "REJECTED"

            if dry_run:
                typer.echo("dry-run complete")
                typer.echo("run_status=REJECTED all variants dead after targeted revise")
                raise typer.Exit(code=2)

            _write_rejected_trace(target_dir, trace)
            raise typer.Exit(code=2)

        if not lint_report["pass"]:
            warning_report = "lint failed after targeted revise; output best draft"

    lint_before_postprocess = lint_report
    lint_report = lint_payload(payload, trace=trace)
    _sync_chosen_variant(payload)

    trace["variant_rank"] = variant_rank
    trace["postprocess"] = {
        "lint_before_postprocess": lint_before_postprocess,
        "lint_after_postprocess": lint_report,
    }
    if revise_evidence:
        trace["revise_evidence"] = revise_evidence
    trace["lint_report"] = lint_report
    trace["llm_calls"] = llm_calls
    trace["max_llm_calls_per_run"] = 2
    _apply_retrieval_profile_decision(trace)

    hard_reject = bool(lint_report.get("is_dead", False)) or (
        str(lint_report.get("all_dead_run_status", "")).strip().upper() == "REJECTED"
    )
    if hard_reject:
        trace["run_status"] = "REJECTED"
        if dry_run:
            typer.echo("dry-run complete")
            typer.echo("run_status=REJECTED hard gate hit")
            raise typer.Exit(code=2)
        _write_rejected_trace(target_dir, trace)
        raise typer.Exit(code=2)

    craft_score = float(lint_report.get("craft_score", 0.0) or 0.0)
    if craft_score < 0.85:
        _fail_quality_floor(target_dir, trace, dry_run=dry_run)

    if dry_run:
        typer.echo("dry-run complete")
        typer.echo(f"lint_pass={lint_report['pass']} llm_calls={llm_calls}")
        if verbose:
            typer.echo(
                f"active_profile={trace.get('active_profile','')} profile_source={trace.get('profile_source','')}"
            )
        return

    try:
        write_outputs(payload, target_dir, trace)
    except StructuralIncompleteError as exc:
        if llm_calls >= 2:
            trace["run_status"] = "REJECTED"
            trace["structural_error"] = str(exc)
            _write_rejected_trace(target_dir, trace)
            raise typer.Exit(code=2)

        try:
            revised_payload, revise_trace = generate_lyric_payload(
                user_input,
                repo_root=repo_root,
                targeted_revise_prompt=STRUCTURAL_REVISE_PROMPT,
            )
        except Exception as revise_exc:
            trace["run_status"] = "REJECTED"
            trace["error_stage"] = "structural_targeted_revise_generation"
            trace["error_type"] = type(revise_exc).__name__
            trace["error_message"] = str(revise_exc)
            _write_rejected_trace(target_dir, trace)
            raise typer.Exit(code=2)
        payload, variant_rank = _score_variants(revised_payload, trace=trace)
        lint_report = lint_payload(payload, trace=trace)
        _sync_chosen_variant(payload)
        llm_calls = 2
        usage_prev = trace.get("usage", {})
        usage_next = revise_trace.get("usage", {})
        trace["usage"] = {
            "input_tokens": int(usage_prev.get("input_tokens", 0)) + int(usage_next.get("input_tokens", 0)),
            "output_tokens": int(usage_prev.get("output_tokens", 0)) + int(usage_next.get("output_tokens", 0)),
            "total_tokens": int(usage_prev.get("total_tokens", 0)) + int(usage_next.get("total_tokens", 0)),
        }
        _merge_revise_trace_metadata(trace, revise_trace)
        trace["revise_trace"] = revise_trace
        trace["revise_evidence"] = {
            "targeted_revise_prompt": STRUCTURAL_REVISE_PROMPT,
            "trigger": "StructuralIncompleteError",
            "structural_error": str(exc),
            "revised_lint_report": lint_report,
        }
        trace["structural_revise_triggered"] = True
        trace["variant_rank"] = variant_rank
        trace["lint_report"] = lint_report
        trace["llm_calls"] = llm_calls
        trace["max_llm_calls_per_run"] = 2
        _apply_retrieval_profile_decision(trace)

        hard_reject = bool(lint_report.get("is_dead", False)) or (
            str(lint_report.get("all_dead_run_status", "")).strip().upper() == "REJECTED"
        )
        if hard_reject:
            trace["run_status"] = "REJECTED"
            _write_rejected_trace(target_dir, trace)
            raise typer.Exit(code=2)

        craft_score = float(lint_report.get("craft_score", 0.0) or 0.0)
        if craft_score < 0.85:
            _fail_quality_floor(target_dir, trace, dry_run=False)

        try:
            write_outputs(payload, target_dir, trace)
        except StructuralIncompleteError as second_exc:
            trace["run_status"] = "REJECTED"
            trace["structural_error"] = str(second_exc)
            _write_rejected_trace(target_dir, trace)
            raise typer.Exit(code=2)
    if warning_report:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "warning_report.md").write_text(warning_report + "\n", encoding="utf-8")

    if verbose:
        typer.echo(f"lint_report={lint_report}")
        typer.echo(
            f"active_profile={trace.get('active_profile','')} profile_source={trace.get('profile_source','')}"
        )

    typer.echo(
        f"generated {target_dir / 'lyrics.txt'} | {target_dir / 'style.txt'} | {target_dir / 'exclude.txt'}"
    )


if __name__ == "__main__":
    app()
