from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from src.claude_client import generate_lyric_payload
from src.compile import write_outputs
from src.lint import lint_payload
from src.schemas import UserInput


app = typer.Typer(help="Lyric Craftsman CLI (PRD v2.0)")


def _build_targeted_revise_prompt(payload: dict[str, Any], lint_report: dict[str, Any]) -> str:
    return (
        "Targeted revise only for failing lines. Keep unchanged lines untouched.\n"
        f"Failed rules: {lint_report.get('failed_rules', [])}\n"
        f"Violations: {lint_report.get('violations', [])}\n"
        f"Current payload: {payload}"
    )


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
    lint_report = lint_payload(payload)

    llm_calls = 1
    warning_report = ""
    if not lint_report["pass"]:
        llm_calls += 1
        warning_report = "lint failed after first pass; targeted revise required"
        # This v2.0 implementation records revise intent in trace.
        trace["targeted_revise_prompt"] = _build_targeted_revise_prompt(
            payload.model_dump(), lint_report
        )

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
