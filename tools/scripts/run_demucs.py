"""Isolated Demucs runner.

Child process only: write unified JSON result, never raise to parent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path


def _write_result(path: Path, data: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--result-json", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.output_dir)
    result_path = Path(args.result_json)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = {
        "ok": False,
        "status": "error",
        "stems_dir": str(out_dir),
        "vocals": str(input_path),
        "drums": str(input_path),
        "bass": str(input_path),
        "other": str(input_path),
        "backing": str(input_path),
        "error": "",
    }

    try:
        if not input_path.exists():
            base["error"] = f"input not found: {input_path}"
            _write_result(result_path, base)
            return 0

        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "--two-stems=vocals",
            "-n",
            "htdemucs_ft",
            "-o",
            str(out_dir),
            str(input_path),
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, check=False
        )

        model_dir = out_dir / "htdemucs_ft" / input_path.stem
        vocals = model_dir / "vocals.wav"
        no_vocals = model_dir / "no_vocals.wav"

        if (
            proc.returncode == 0
            and model_dir.exists()
            and vocals.exists()
            and no_vocals.exists()
        ):
            _write_result(
                result_path,
                {
                    "ok": True,
                    "status": "ok",
                    "stems_dir": str(model_dir),
                    "vocals": str(vocals),
                    "drums": str(no_vocals),
                    "bass": str(no_vocals),
                    "other": str(no_vocals),
                    "backing": str(no_vocals),
                    "error": "",
                },
            )
            return 0

        base["error"] = (
            f"demucs failed: rc={proc.returncode}; stderr={proc.stderr.strip()[:200]}"
        )
        _write_result(result_path, base)
        return 0

    except Exception as exc:
        base["error"] = str(exc)
        _write_result(result_path, base)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
