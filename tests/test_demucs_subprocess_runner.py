from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


def _write_child_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_run_demucs_subprocess_success_json(tmp_path: Path) -> None:
    from producer_tools.business.demucs_subprocess_runner import run_demucs_subprocess

    input_audio = tmp_path / "take.mp3"
    input_audio.write_bytes(b"audio")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    child = tmp_path / "child_ok.py"
    _write_child_script(
        child,
        """
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--input'); p.add_argument('--output-dir'); p.add_argument('--result-json')
a=p.parse_args()
Path(a.output_dir).mkdir(parents=True, exist_ok=True)
r={
  'ok': True, 'status':'ok', 'stems_dir': a.output_dir,
  'vocals': a.input, 'drums': a.input, 'bass': a.input, 'other': a.input, 'backing': a.input,
  'error': ''
}
Path(a.result_json).write_text(json.dumps(r), encoding='utf-8')
""".strip(),
    )

    result = run_demucs_subprocess(
        input_path=str(input_audio),
        output_dir=str(out_dir),
        timeout_sec=5,
        runner_script=str(child),
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["stems_dir"] == str(out_dir)
    assert result["vocals"] == str(input_audio)


def test_run_demucs_subprocess_timeout_fallback(tmp_path: Path) -> None:
    from producer_tools.business.demucs_subprocess_runner import run_demucs_subprocess

    input_audio = tmp_path / "take.mp3"
    input_audio.write_bytes(b"audio")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    child = tmp_path / "child_sleep.py"
    _write_child_script(
        child,
        """
import argparse, time
p=argparse.ArgumentParser(); p.add_argument('--input'); p.add_argument('--output-dir'); p.add_argument('--result-json')
p.parse_args()
time.sleep(2)
""".strip(),
    )

    result = run_demucs_subprocess(
        input_path=str(input_audio),
        output_dir=str(out_dir),
        timeout_sec=0.2,
        runner_script=str(child),
    )

    assert result["ok"] is False
    assert result["status"] == "fallback"
    assert result["fallback_reason"] == "timeout"
    # unified complete fields
    for key in ["stems_dir", "vocals", "drums", "bass", "other", "backing", "error"]:
        assert key in result


def test_run_demucs_subprocess_child_error_json_fallback(tmp_path: Path) -> None:
    from producer_tools.business.demucs_subprocess_runner import run_demucs_subprocess

    input_audio = tmp_path / "take.mp3"
    input_audio.write_bytes(b"audio")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    child = tmp_path / "child_fail.py"
    _write_child_script(
        child,
        """
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--input'); p.add_argument('--output-dir'); p.add_argument('--result-json')
a=p.parse_args()
r={'ok': False, 'status':'error', 'error':'demucs failed'}
Path(a.result_json).write_text(json.dumps(r), encoding='utf-8')
""".strip(),
    )

    result = run_demucs_subprocess(
        input_path=str(input_audio),
        output_dir=str(out_dir),
        timeout_sec=5,
        runner_script=str(child),
    )

    assert result["ok"] is False
    assert result["status"] == "fallback"
    assert result["fallback_reason"] == "child_error"
    assert "demucs failed" in result["error"]
