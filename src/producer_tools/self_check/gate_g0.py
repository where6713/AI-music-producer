from __future__ import annotations

from pathlib import Path
import subprocess


REQUIRED_HOOKS = ["pre-commit", "commit-msg", "pre-push", "post-commit"]


def _read_hooks_path(workspace_root: Path) -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=str(workspace_root),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None
    return output or None


def check_gate_g0(
    workspace_root: Path,
    *,
    strict_hooks_path: bool = True,
) -> dict[str, object]:
    hooks_dir = workspace_root / "tools" / "githooks"
    missing_hooks = [name for name in REQUIRED_HOOKS if not (hooks_dir / name).is_file()]

    warnings: list[str] = []
    hooks_path = _read_hooks_path(workspace_root)
    hooks_path_ok = hooks_path == "tools/githooks"

    if strict_hooks_path and not hooks_path_ok:
        warnings.append(
            "core.hooksPath is not tools/githooks; run: git config core.hooksPath tools/githooks"
        )

    status = "pass"
    if missing_hooks:
        status = "fail"
    elif strict_hooks_path and not hooks_path_ok:
        status = "fail"

    return {
        "status": status,
        "workspace_root": str(workspace_root.resolve()),
        "required_hooks": REQUIRED_HOOKS,
        "missing_hooks": missing_hooks,
        "hooks_path": hooks_path,
        "hooks_path_ok": hooks_path_ok,
        "warnings": warnings,
    }
