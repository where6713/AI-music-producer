from __future__ import annotations

from pathlib import Path
import sys

import click
import typer

from src.main import produce as produce_v2
from src.producer_tools.self_check.gate_g0 import check_gate_g0
from src.producer_tools.self_check.gate_g1 import check_gate_g1
from src.producer_tools.self_check.gate_g2 import validate_failure_evidence
from src.producer_tools.self_check.gate_g3 import validate_pass_evidence
from src.producer_tools.self_check.gate_g4 import validate_docs_alignment
from src.producer_tools.self_check.gate_g5 import check_gate_g5
from src.producer_tools.self_check.gate_g6 import check_gate_g6
from src.producer_tools.self_check.gate_g7 import check_gate_g7


app = typer.Typer(
    help="AI music producer CLI (PRD v2.0)",
    rich_markup_mode=None,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


def _ensure_utf8_output() -> None:
    stdout_reconf = getattr(sys.stdout, "reconfigure", None)
    if callable(stdout_reconf):
        try:
            stdout_reconf(encoding="utf-8", errors="replace")
        except Exception:
            pass


@app.command()
def status() -> None:
    typer.echo("AI music producer ready")


@app.command("self-check")
def self_check(
    gate: str = typer.Argument(..., help="Gate name, currently supports: g0"),
    strict_hooks_path: bool = typer.Option(
        True,
        "--strict-hooks-path",
        help="Fail when core.hooksPath is not tools/githooks.",
    ),
) -> None:
    if gate.strip().lower() != "g0":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)

    result = check_gate_g0(Path.cwd(), strict_hooks_path=strict_hooks_path)
    if result["status"] == "pass":
        typer.echo("G0 PASS")
        return
    typer.echo("G0 FAIL")
    missing_hooks = result.get("missing_hooks", [])
    missing_docs = result.get("missing_docs", [])
    if missing_hooks:
        typer.echo("missing_hooks: " + ", ".join(missing_hooks))
    if missing_docs:
        typer.echo("missing_docs: " + ", ".join(missing_docs))
    raise typer.Exit(code=1)


@app.command("failure-evidence-check")
def failure_evidence_check(
    symptom: str = typer.Argument(...),
    trigger_condition: str = typer.Argument(...),
    root_cause: str = typer.Argument(...),
    failure_command: str = typer.Argument(...),
) -> None:
    result = validate_failure_evidence(
        {
            "symptom": symptom,
            "trigger_condition": trigger_condition,
            "root_cause": root_cause,
            "failure_command": failure_command,
        }
    )
    if result["status"] == "pass":
        typer.echo("G2 FAILURE-EVIDENCE PASS")
        return
    typer.echo("G2 FAILURE-EVIDENCE FAIL")
    raise typer.Exit(code=1)


@app.command("scope-check")
def scope_check(
    gate: str = typer.Argument(...),
) -> None:
    if gate.strip().lower() != "g1":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)

    result = check_gate_g1(Path.cwd())
    if result["status"] == "pass":
        typer.echo("G1 SCOPE-CHECK PASS")
        return

    typer.echo("G1 SCOPE-CHECK FAIL")
    failed = result.get("failed_checks", [])
    if failed:
        typer.echo("failed_checks: " + ", ".join(failed))
    raise typer.Exit(code=1)


@app.command("pass-evidence-check")
def pass_evidence_check(
    local_command: str = typer.Argument(...),
    local_result: str = typer.Argument(...),
    ci_result: str = typer.Argument(...),
    ci_run_url: str = typer.Argument(...),
    reproducible_command_1: str = typer.Argument(...),
    reproducible_command_2: str = typer.Argument(...),
) -> None:
    result = validate_pass_evidence(
        {
            "local_command": local_command,
            "local_result": local_result,
            "ci_result": ci_result,
            "ci_run_url": ci_run_url,
            "reproducible_commands": [reproducible_command_1, reproducible_command_2],
        }
    )
    if result["status"] == "pass":
        typer.echo("G3 PASS-EVIDENCE PASS")
        return
    typer.echo("G3 PASS-EVIDENCE FAIL")
    raise typer.Exit(code=1)


@app.command("docs-alignment-check")
def docs_alignment_check(
    prd_path: str = typer.Argument(...),
    pm_role_path: str = typer.Argument(...),
    pm_rules_path: str = typer.Argument(...),
    delivery_file_1: str = typer.Argument(...),
    delivery_file_2: str = typer.Argument(...),
    delivery_file_3: str = typer.Argument(...),
) -> None:
    result = validate_docs_alignment(
        {
            "prd_path": prd_path,
            "pm_role_path": pm_role_path,
            "pm_rules_path": pm_rules_path,
            "delivery_files": [delivery_file_1, delivery_file_2, delivery_file_3],
            "field_name_conflicts": [],
        }
    )
    if result["status"] == "pass":
        typer.echo("G4 DOCS-ALIGNMENT PASS")
        return
    typer.echo("G4 DOCS-ALIGNMENT FAIL")
    raise typer.Exit(code=1)


@app.command("hook-check")
def hook_check(gate: str = typer.Argument(...)) -> None:
    if gate.strip().lower() != "g5":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)
    result = check_gate_g5(Path.cwd())
    if result["status"] == "pass":
        typer.echo("G5 HOOK-CHECK PASS")
        return
    typer.echo("G5 HOOK-CHECK FAIL")
    raise typer.Exit(code=1)


@app.command("ci-gate-check")
def ci_gate_check(gate: str = typer.Argument(...)) -> None:
    if gate.strip().lower() != "g6":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)
    result = check_gate_g6(Path.cwd())
    if result["status"] == "pass":
        typer.echo("G6 CI-GATE PASS")
        return
    typer.echo("G6 CI-GATE FAIL")
    raise typer.Exit(code=1)


@app.command(
    "gate-check",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def gate_check() -> None:
    args = list(click.get_current_context().args)
    all_mode = "--all" in args
    run_proof = "--run-proof" in args

    if not all_mode:
        typer.echo("Use --all for G7 total closure check")
        raise typer.Exit(code=2)

    result = check_gate_g7(Path.cwd(), run_proof=run_proof)
    summary = result.get("gate_summary", {})
    typer.echo(" ".join([f"{k}={v}" for k, v in summary.items()]))
    if result["status"] == "pass":
        typer.echo("G7 TOTAL-CLOSURE PASS")
        return
    typer.echo("G7 TOTAL-CLOSURE FAIL")
    raise typer.Exit(code=1)


@app.command("pm-audit")
def pm_audit() -> None:
    result = check_gate_g7(Path.cwd(), run_proof=True)
    if result["status"] != "pass":
        typer.echo("PM AUDIT FAIL")
        typer.echo(str(result))
        raise typer.Exit(code=1)
    typer.echo("PM AUDIT PASS")
    typer.echo(str(result))


@app.command("produce")
def produce_command(
    raw_intent: str = typer.Argument(...),
    genre: str = typer.Option("", "--genre"),
    mood: str = typer.Option("", "--mood"),
    vocal: str = typer.Option("any", "--vocal"),
    lang: str = typer.Option("zh-CN", "--lang"),
    out_dir: str = typer.Option("out", "--out-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    produce_v2(
        raw_intent=raw_intent,
        genre=genre,
        mood=mood,
        vocal=vocal,
        lang=lang,
        out_dir=out_dir,
        verbose=verbose,
        dry_run=dry_run,
    )


def main() -> None:
    _ensure_utf8_output()
    app()


if __name__ == "__main__":
    main()
