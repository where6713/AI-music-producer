from __future__ import annotations

from pathlib import Path
import sys
import argparse
import os

import click
import typer
from rich.console import Console
from rich.table import Table

from src.main import produce as produce_v2
from src.profile_router import AmbiguousProfileError
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
)

PM_AUDIT_CHECK_ORDER = [
    "chosen_variant_not_dead",
    "craft_score_floor",
    "r14_r16_global_hits",
    "few_shot_no_numeric_ids",
    "audit_sections_complete",
    "lyrics_no_residuals",
    "postprocess_symbols_absent",
    "profile_source_recorded",
]


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
    failure_output: str = typer.Argument(...),
) -> None:
    result = validate_failure_evidence(
        {
            "symptom": symptom,
            "trigger_condition": trigger_condition,
            "root_cause": root_cause,
            "failure_command": failure_command,
            "failure_output": failure_output,
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
    local_output: str = typer.Argument(...),
    ci_output: str = typer.Argument(...),
) -> None:
    result = validate_pass_evidence(
        {
            "local_command": local_command,
            "local_result": local_result,
            "ci_result": ci_result,
            "ci_run_url": ci_run_url,
            "reproducible_commands": [reproducible_command_1, reproducible_command_2],
            "local_output": local_output,
            "ci_output": ci_output,
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
    manifest_path: str = typer.Argument(...),
    delivery_file_1: str = typer.Argument(...),
    delivery_file_2: str = typer.Argument(...),
    delivery_file_3: str = typer.Argument(...),
) -> None:
    result = validate_docs_alignment(
        {
            "prd_path": prd_path,
            "pm_role_path": pm_role_path,
            "pm_rules_path": pm_rules_path,
            "manifest_path": manifest_path,
            "delivery_files": [delivery_file_1, delivery_file_2, delivery_file_3],
            "field_name_conflicts": [],
        }
    )
    if result["status"] == "pass":
        typer.echo("G4 DOCS-ALIGNMENT PASS")
        return
    typer.echo("G4 DOCS-ALIGNMENT FAIL")
    failed = result.get("failed_checks", [])
    if failed:
        typer.echo("failed_checks: " + ", ".join(failed))
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


@app.command(
    "pm-audit",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def pm_audit() -> None:
    args = list(click.get_current_context().args)
    last = "--last" in args

    run_id_value = ""
    if "--run-id" in args:
        idx = args.index("--run-id")
        if idx + 1 >= len(args):
            typer.echo("missing value for --run-id")
            raise typer.Exit(code=2)
        run_id_value = str(args[idx + 1]).strip()
        if not run_id_value or run_id_value.startswith("--"):
            typer.echo("missing value for --run-id")
            raise typer.Exit(code=2)

    if last and run_id_value:
        typer.echo("parameter conflict: use either --last or --run-id")
        raise typer.Exit(code=2)

    target_out = Path.cwd() / "out"
    if run_id_value:
        target_out = Path.cwd() / "out" / "task011_runs" / run_id_value
        if not target_out.exists() or not target_out.is_dir():
            typer.echo(f"run-id path not found: {target_out}")
            raise typer.Exit(code=2)

    result = check_gate_g7(
        Path.cwd(),
        run_proof=True,
        strict_pm_audit=True,
        proof_output_dir=target_out,
    )
    proof = result.get("proof", {}) if isinstance(result, dict) else {}
    checks = proof.get("pm_audit_checks", {}) if isinstance(proof, dict) else {}

    no_color = os.getenv("NO_COLOR", "").strip() != ""
    console = Console(no_color=no_color)
    table = Table(title="PM Audit", show_lines=False)
    table.add_column("check_key", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("ok", no_wrap=True)
    table.add_column("detail")

    pass_count = 0
    for name in PM_AUDIT_CHECK_ORDER:
        item = checks.get(name, {}) if isinstance(checks, dict) else {}
        ok = bool(item.get("ok", False))
        if ok:
            status = "[green]PASS[/green]"
            pass_count += 1
        else:
            status = "[red]FAIL[/red]"
        detail = str(item.get("detail", ""))
        table.add_row(name, status, "true" if ok else "false", detail)

    fail_count = len(PM_AUDIT_CHECK_ORDER) - pass_count
    failed_gates = result.get("failed_gates", []) if isinstance(result, dict) else []
    failed_gate_details = result.get("failed_gate_details", {}) if isinstance(result, dict) else {}
    gate_fail_count = len([x for x in failed_gates if str(x).strip()])
    exit_code = 0 if fail_count == 0 and gate_fail_count == 0 else 1
    console.print(table)
    if gate_fail_count > 0:
        typer.echo("FAILED_GATES: " + ", ".join([str(x) for x in failed_gates]))
        if isinstance(failed_gate_details, dict):
            for gate_name in failed_gates:
                detail = failed_gate_details.get(str(gate_name), {})
                if not isinstance(detail, dict):
                    continue
                failed_checks = detail.get("failed_checks", [])
                if isinstance(failed_checks, list) and failed_checks:
                    typer.echo(
                        "FAILED_GATE_DETAIL "
                        + str(gate_name)
                        + ": failed_checks="
                        + ",".join([str(x) for x in failed_checks])
                    )
    typer.echo(f"TOTAL: 8, PASS: {pass_count}, FAIL: {fail_count}, EXIT: {exit_code}")
    if exit_code != 0:
        raise typer.Exit(code=1)


def produce_command(
    raw_intent: str,
    genre: str = "",
    mood: str = "",
    vocal: str = "any",
    profile: str = "",
    lang: str = "zh-CN",
    out_dir: str = "out",
    verbose: bool = False,
    dry_run: bool = False,
) -> None:
    try:
        produce_v2(
            raw_intent=raw_intent,
            genre=genre,
            mood=mood,
            vocal=vocal,
            profile=profile,
            lang=lang,
            out_dir=out_dir,
            verbose=verbose,
            dry_run=dry_run,
        )
    except AmbiguousProfileError as err:
        typer.echo("ambiguous profile, please choose with --profile:")
        for row in err.candidates:
            typer.echo(
                f"- {row.get('profile_id','')} | {row.get('display_name','')} | {row.get('craft_focus','')}"
            )
        raise typer.Exit(code=1)


def _dispatch_produce_from_argv(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m apps.cli.main produce")
    parser.add_argument("raw_intent")
    parser.add_argument("--genre", default="")
    parser.add_argument("--mood", default="")
    parser.add_argument("--vocal", default="any")
    parser.add_argument("--profile", default="")
    parser.add_argument("--lang", default="zh-CN")
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args(argv)
    produce_command(
        raw_intent=ns.raw_intent,
        genre=ns.genre,
        mood=ns.mood,
        vocal=ns.vocal,
        profile=ns.profile,
        lang=ns.lang,
        out_dir=ns.out_dir,
        verbose=ns.verbose,
        dry_run=ns.dry_run,
    )


def main() -> None:
    _ensure_utf8_output()
    # TODO(v3.0): unify CLI framework; current produce path uses argparse while others use Typer.
    if len(sys.argv) > 1 and sys.argv[1] == "produce":
        try:
            _dispatch_produce_from_argv(sys.argv[2:])
        except click.exceptions.Exit as err:
            raise SystemExit(err.exit_code)
        return
    app()


if __name__ == "__main__":
    main()
