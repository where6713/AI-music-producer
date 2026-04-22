from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from src.claude_client import generate_lyric_payload
from src.compile import write_outputs
from src.lint import lint_payload
from src.schemas import LyricPayload, UserInput


app = typer.Typer(help="Lyric Craftsman CLI (PRD v2.0)")


def _build_targeted_revise_prompt(payload: dict[str, Any], lint_report: dict[str, Any]) -> str:
    return (
        "Targeted revise only for failing lines. Keep unchanged lines untouched.\n"
        f"Failed rules: {lint_report.get('failed_rules', [])}\n"
        f"Violations: {lint_report.get('violations', [])}\n"
        f"Current payload: {payload}"
    )


def _score_variants(payload: LyricPayload) -> tuple[LyricPayload, dict[str, Any]]:
    scored: list[tuple[str, int, int]] = []
    for variant in payload.variants:
        probe = payload.model_copy(deep=True)
        probe.lyrics_by_section = variant.lyrics_by_section
        report = lint_payload(probe)
        passed_rules = 13 - len(report.get("failed_rules", []))
        variant.lint_result.passed_rules = passed_rules
        variant.lint_result.failed_rules = list(report.get("failed_rules", []))
        scored.append((variant.variant_id, passed_rules, len(report.get("failed_rules", []))))

    scored.sort(key=lambda x: (-x[1], x[2], x[0]))
    ranking = {variant_id: idx for idx, (variant_id, _, _) in enumerate(scored, start=1)}
    for variant in payload.variants:
        variant.lint_result.rank = ranking.get(variant.variant_id, 99)

    chosen_variant_id = scored[0][0] if scored else payload.chosen_variant_id
    payload.chosen_variant_id = chosen_variant_id
    for variant in payload.variants:
        if variant.variant_id == chosen_variant_id:
            payload.lyrics_by_section = variant.lyrics_by_section
            break

    return payload, {"ranking": scored, "chosen_variant_id": chosen_variant_id}


@app.command("produce")
def produce(
    raw_intent: str = typer.Argument(...),
    genre: str = typer.Option("", "--genre"),
    mood: str = typer.Option("", "--mood"),
    vocal: str = typer.Option("any", "--vocal"),
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
    )

    payload, trace = generate_lyric_payload(user_input, repo_root=repo_root)
    payload, variant_rank = _score_variants(payload)
    lint_report = lint_payload(payload)

    llm_calls = 1
    warning_report = ""
    revise_evidence: dict[str, Any] = {}
    if not lint_report["pass"]:
        targeted_prompt = _build_targeted_revise_prompt(
            payload.model_dump(), lint_report
        )
        revised_payload, revise_trace = generate_lyric_payload(
            user_input,
            repo_root=repo_root,
            targeted_revise_prompt=targeted_prompt,
        )
        revised_payload, revised_rank = _score_variants(revised_payload)
        revised_lint = lint_payload(revised_payload)
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
        trace["revise_trace"] = revise_trace
        revise_evidence = {
            "targeted_revise_prompt": targeted_prompt,
            "initial_failed_rules": variant_rank,
            "revised_failed_rules": revised_rank,
            "revised_lint_report": revised_lint,
        }
        if not lint_report["pass"]:
            warning_report = "lint failed after targeted revise; output best draft"

    trace["variant_rank"] = variant_rank
    if revise_evidence:
        trace["revise_evidence"] = revise_evidence
    trace["lint_report"] = lint_report
    trace["llm_calls"] = llm_calls
    trace["max_llm_calls_per_run"] = 2

    if dry_run:
        typer.echo("dry-run complete")
        typer.echo(f"lint_pass={lint_report['pass']} llm_calls={llm_calls}")
        return

    write_outputs(payload, target_dir, trace)
    if warning_report:
        (target_dir / "warning_report.md").write_text(warning_report + "\n", encoding="utf-8")

    if verbose:
        typer.echo(f"lint_report={lint_report}")

    typer.echo(
        f"generated {target_dir / 'lyrics.txt'} | {target_dir / 'style.txt'} | {target_dir / 'exclude.txt'}"
    )


if __name__ == "__main__":
    app()
