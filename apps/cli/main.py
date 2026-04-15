from pathlib import Path
import json

import click
import typer

from apps.cli.memory import get_project_memory_context
from apps.cli.translation import translate_result

app = typer.Typer(
    help="AI music producer CLI",
    rich_markup_mode=None,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


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
    app()


if __name__ == "__main__":
    main()
