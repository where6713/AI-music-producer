"""Minimal subprocess wrapper for isolated Demucs execution.

Python 3.13 compatible, timeout + fallback, unified return schema.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _fallback_result(
    input_path: str,
    output_dir: str,
    reason: str,
    error: str,
    result_json: str,
) -> dict[str, object]:
    return {
        "ok": False,
        "status": "fallback",
        "fallback_reason": reason,
        "stems_dir": output_dir,
        "vocals": input_path,
        "drums": input_path,
        "bass": input_path,
        "other": input_path,
        "backing": input_path,
        "error": error,
        "result_json": result_json,
    }


def run_demucs_subprocess(
    input_path: str,
    output_dir: str,
    timeout_sec: float = 60.0,
    runner_script: str | None = None,
) -> dict[str, object]:
    """Run isolated demucs script and return unified schema.

    Main process never imports demucs/torchaudio directly.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result_json = out_dir / "result.json"

    script = (
        Path(runner_script)
        if runner_script
        else Path(__file__).resolve().parents[3] / "tools" / "scripts" / "run_demucs.py"
    )

    cmd = [
        sys.executable,
        str(script),
        "--input",
        input_path,
        "--output-dir",
        str(out_dir),
        "--result-json",
        str(result_json),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _fallback_result(
            input_path=input_path,
            output_dir=str(out_dir),
            reason="timeout",
            error=f"demucs subprocess timeout ({timeout_sec}s)",
            result_json=str(result_json),
        )

    if not result_json.exists():
        return _fallback_result(
            input_path=input_path,
            output_dir=str(out_dir),
            reason="result_missing",
            error=f"result.json missing; rc={proc.returncode}; stderr={proc.stderr.strip()[:200]}",
            result_json=str(result_json),
        )

    try:
        child = json.loads(result_json.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fallback_result(
            input_path=input_path,
            output_dir=str(out_dir),
            reason="result_parse_error",
            error=str(exc),
            result_json=str(result_json),
        )

    if isinstance(child, dict) and child.get("ok") is True:
        return {
            "ok": True,
            "status": str(child.get("status", "ok")),
            "stems_dir": str(child.get("stems_dir", out_dir)),
            "vocals": str(child.get("vocals", input_path)),
            "drums": str(child.get("drums", input_path)),
            "bass": str(child.get("bass", input_path)),
            "other": str(child.get("other", input_path)),
            "backing": str(child.get("backing", input_path)),
            "error": str(child.get("error", "")),
            "result_json": str(result_json),
        }

    return _fallback_result(
        input_path=input_path,
        output_dir=str(out_dir),
        reason="child_error",
        error=str(child.get("error", "child returned error"))
        if isinstance(child, dict)
        else "child returned non-dict",
        result_json=str(result_json),
    )
