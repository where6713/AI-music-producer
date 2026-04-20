from pathlib import Path
import json
import os
import sys

import click
import typer

from apps.cli.memory import get_project_memory_context
from apps.cli.translation import translate_result
from src.producer_tools.self_check.gate_g0 import check_gate_g0
from src.producer_tools.self_check.gate_g2 import validate_failure_evidence
from src.producer_tools.self_check.gate_g3 import validate_pass_evidence
from src.producer_tools.self_check.gate_g4 import validate_docs_alignment
from src.producer_tools.self_check.gate_g5 import check_gate_g5
from src.producer_tools.self_check.gate_g6 import check_gate_g6
from src.producer_tools.self_check.gate_g7 import check_gate_g7

app = typer.Typer(
    help="AI music producer CLI",
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
    stderr_reconf = getattr(sys.stderr, "reconfigure", None)
    if callable(stderr_reconf):
        try:
            stderr_reconf(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _load_dotenv_if_exists() -> None:
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@app.callback()
def cli() -> None:
    """Root command group."""


@app.command()
def status() -> None:
    typer.echo(translate_result("status_ready", "ok"))


@app.command()
def context() -> None:
    summary = get_project_memory_context()
    if summary:
        typer.echo(summary)
        return
    typer.echo(translate_result("context_empty", "ok"))


@app.command("self-check")
def self_check(
    gate: str = typer.Argument(..., help="Gate name, currently supports: g0"),
    strict_hooks_path: bool = typer.Option(
        True,
        "--strict-hooks-path",
        help="Fail when core.hooksPath is not tools/githooks.",
    ),
) -> None:
    gate_name = gate.strip().lower()
    if gate_name != "g0":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)

    result = check_gate_g0(Path.cwd(), strict_hooks_path=strict_hooks_path)
    if result.get("status") == "pass":
        typer.echo("G0 PASS")
        return

    typer.echo("G0 FAIL")
    for warning in result.get("warnings", []):
        typer.echo(f"- {warning}")
    raise typer.Exit(code=1)


@app.command("failure-evidence-check")
def failure_evidence_check(
    symptom: str = typer.Argument(..., help="Observed failure symptom."),
    trigger_condition: str = typer.Argument(
        ..., help="How the failure is triggered."
    ),
    root_cause: str = typer.Argument(..., help="Analyzed root cause."),
    failure_command: str = typer.Argument(
        ..., help="Command that reproduces the failure."
    ),
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
    missing = ", ".join(result["missing_fields"])
    typer.echo(f"missing_fields: {missing}")
    raise typer.Exit(code=1)


@app.command("pass-evidence-check")
def pass_evidence_check(
    local_command: str = typer.Argument(..., help="Local verification command."),
    local_result: str = typer.Argument(..., help="Local result status."),
    ci_result: str = typer.Argument(..., help="CI result status."),
    ci_run_url: str = typer.Argument(..., help="CI run URL."),
    reproducible_command_1: str = typer.Argument(..., help="Repro command 1."),
    reproducible_command_2: str = typer.Argument(..., help="Repro command 2."),
) -> None:
    result = validate_pass_evidence(
        {
            "local_command": local_command,
            "local_result": local_result,
            "ci_result": ci_result,
            "ci_run_url": ci_run_url,
            "reproducible_commands": [
                reproducible_command_1,
                reproducible_command_2,
            ],
        }
    )

    if result["status"] == "pass":
        typer.echo("G3 PASS-EVIDENCE PASS")
        return

    typer.echo("G3 PASS-EVIDENCE FAIL")
    missing = ", ".join(result["missing_fields"])
    if missing:
        typer.echo(f"missing_fields: {missing}")
    for warning in result.get("warnings", []):
        typer.echo(f"- {warning}")
    raise typer.Exit(code=1)


@app.command("docs-alignment-check")
def docs_alignment_check(
    prd_path: str = typer.Argument(..., help="PRD path."),
    pm_role_path: str = typer.Argument(..., help="PM role path."),
    pm_rules_path: str = typer.Argument(..., help="PM rules path."),
    delivery_file_1: str = typer.Argument(..., help="Delivery file path 1."),
    delivery_file_2: str = typer.Argument(..., help="Delivery file path 2."),
    delivery_file_3: str = typer.Argument(..., help="Delivery file path 3."),
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
    failed = ", ".join(result["failed_checks"])
    typer.echo(f"failed_checks: {failed}")
    for warning in result.get("warnings", []):
        typer.echo(f"- {warning}")
    raise typer.Exit(code=1)


@app.command("hook-check")
def hook_check(
    gate: str = typer.Argument(..., help="Gate name, currently supports: g5"),
) -> None:
    gate_name = gate.strip().lower()
    if gate_name != "g5":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)

    result = check_gate_g5(Path.cwd())
    if result["status"] == "pass":
        typer.echo("G5 HOOK-CHECK PASS")
        return

    typer.echo("G5 HOOK-CHECK FAIL")
    failed = ", ".join(result["failed_checks"])
    typer.echo(f"failed_checks: {failed}")
    for warning in result.get("warnings", []):
        typer.echo(f"- {warning}")
    raise typer.Exit(code=1)


@app.command("ci-gate-check")
def ci_gate_check(
    gate: str = typer.Argument(..., help="Gate name, currently supports: g6"),
) -> None:
    gate_name = gate.strip().lower()
    if gate_name != "g6":
        typer.echo(f"Unsupported gate: {gate}")
        raise typer.Exit(code=2)

    result = check_gate_g6(Path.cwd())
    if result["status"] == "pass":
        typer.echo("G6 CI-GATE PASS")
        return

    typer.echo("G6 CI-GATE FAIL")
    failed = ", ".join(result["failed_checks"])
    typer.echo(f"failed_checks: {failed}")
    for warning in result.get("warnings", []):
        typer.echo(f"- {warning}")
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
    summary_line = " ".join([f"{k}={v}" for k, v in summary.items()])

    if result["status"] == "pass":
        typer.echo("G7 TOTAL-CLOSURE PASS")
        typer.echo(summary_line)
        if run_proof:
            proof = result.get("proof", {})
            typer.echo(
                f"proof run_id={proof.get('run_id','')} trace_id={proof.get('trace_id','')}"
            )
            typer.echo(f"proof output_dir={proof.get('output_dir','')}")
        return

    typer.echo("G7 TOTAL-CLOSURE FAIL")
    typer.echo(summary_line)
    failed = ", ".join(result.get("failed_gates", []))
    if failed:
        typer.echo(f"failed_gates: {failed}")
    proof = result.get("proof", {})
    if run_proof and proof.get("status") != "pass":
        missing = ", ".join(proof.get("missing_files", []))
        typer.echo(f"proof_failed_missing_files: {missing}")
    raise typer.Exit(code=1)


def enforce_plan_first(plan_path: Path | None, plan_step: str | None) -> None:
    if plan_path is None or plan_step is None or not plan_step.strip():
        typer.echo(translate_result("plan_required", "error"))
        raise typer.Exit(code=1)
    if not plan_path.exists():
        typer.echo(
            translate_result(
                "plan_missing",
                "error",
                {"plan_path": plan_path},
            )
        )
        raise typer.Exit(code=1)


def load_checkpoint(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return None
    return data


def save_checkpoint(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, indent=2)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def produce(
    plan: Path = typer.Argument(..., help="Path to plan file for long-running action."),
    plan_step: str = typer.Argument(
        ..., help="Plan step identifier required before execution."
    ),
) -> None:
    """Run a long-running production action (plan-first guarded)."""
    enforce_plan_first(plan, plan_step)
    checkpoint_path = Path(".sisyphus/runtime/producer_state.json")
    resume = False

    args = list(click.get_current_context().args)
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--resume":
            resume = True
            index += 1
            continue
        if token == "--checkpoint":
            if index + 1 >= len(args):
                typer.echo(translate_result("checkpoint_required", "error"))
                raise typer.Exit(code=1)
            checkpoint_path = Path(args[index + 1])
            index += 2
            continue
        if token.startswith("--checkpoint="):
            checkpoint_path = Path(token.split("=", 1)[1])
            index += 1
            continue
        index += 1

    if resume:
        state = load_checkpoint(checkpoint_path)
        if state is None:
            typer.echo(
                translate_result(
                    "checkpoint_missing",
                    "error",
                    {"checkpoint_path": checkpoint_path},
                )
            )
            raise typer.Exit(code=1)
        resumed_step = state.get("step", plan_step)
        typer.echo(translate_result("resume", "ok", {"step": resumed_step}))
    else:
        save_checkpoint(
            checkpoint_path,
            {"plan": str(plan), "step": plan_step, "status": "started"},
        )

    typer.echo(
        translate_result(
            "plan_acknowledged",
            "ok",
            {"plan_step": plan_step},
        )
    )
    save_checkpoint(
        checkpoint_path,
        {"plan": str(plan), "step": plan_step, "status": "completed"},
    )
    typer.echo(
        translate_result(
            "production_completed",
            "ok",
            {"checkpoint_path": checkpoint_path},
        )
    )


def main() -> None:
    _ensure_utf8_output()
    _load_dotenv_if_exists()
    app()


if __name__ == "__main__":
    main()
