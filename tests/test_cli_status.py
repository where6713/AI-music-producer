import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_status_command_outputs_ready_message() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "status"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "AI music producer ready" in result.stdout


def test_cli_produce_requires_plan_and_step() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "produce"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Plan required for long-running actions" in result.stdout


def test_cli_produce_requires_plan_step() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as temp_plan:
        _ = temp_plan.write(b"test plan")
        temp_plan.flush()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apps.cli.main",
                "produce",
                temp_plan.name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode != 0
    assert "Plan required for long-running actions" in result.stdout


def test_cli_produce_accepts_plan_step() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        plan_path = Path(temp_dir) / "plan.md"
        checkpoint_path = Path(temp_dir) / "producer_state.json"
        plan_path.write_text("test plan", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apps.cli.main",
                "produce",
                str(plan_path),
                "P03.01",
                "--checkpoint",
                str(checkpoint_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0
    assert "Plan acknowledged (P03.01)" in result.stdout


def test_cli_produce_resume_requires_checkpoint_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        plan_path = Path(temp_dir) / "plan.md"
        missing_checkpoint = Path(temp_dir) / "missing_state.json"
        plan_path.write_text("test plan", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apps.cli.main",
                "produce",
                str(plan_path),
                "P03.02",
                "--resume",
                "--checkpoint",
                str(missing_checkpoint),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode != 0
    assert "Checkpoint not found" in result.stdout


def test_cli_produce_creates_completed_checkpoint() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        plan_path = Path(temp_dir) / "plan.md"
        checkpoint_path = Path(temp_dir) / "producer_state.json"
        plan_path.write_text("test plan", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apps.cli.main",
                "produce",
                str(plan_path),
                "P03.02",
                "--checkpoint",
                str(checkpoint_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert checkpoint_path.exists()
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert payload["status"] == "completed"


def test_cli_produce_resume_with_existing_checkpoint() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        plan_path = Path(temp_dir) / "plan.md"
        checkpoint_path = Path(temp_dir) / "producer_state.json"
        plan_path.write_text("test plan", encoding="utf-8")
        checkpoint_path.write_text(
            json.dumps(
                {
                    "plan": str(plan_path),
                    "step": "P03.02",
                    "status": "started",
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apps.cli.main",
                "produce",
                str(plan_path),
                "P03.02",
                "--resume",
                "--checkpoint",
                str(checkpoint_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0
    assert "Resuming from checkpoint" in result.stdout


def test_cli_self_check_g0_reports_pass() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "self-check", "g0"],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G0 PASS" in stdout


def test_cli_failure_evidence_check_reports_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "failure-evidence-check",
            "ModuleNotFoundError in test collection",
            "py -3.13 -m pytest -q tests/test_gate_g2_failure_evidence.py",
            "missing module implementation",
            "py -3.13 -m pytest -q tests/test_gate_g2_failure_evidence.py",
        ],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G2 FAILURE-EVIDENCE PASS" in stdout


def test_cli_pass_evidence_check_reports_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "pass-evidence-check",
            "py -3.13 -m pytest -q",
            "pass",
            "success",
            "https://github.com/where6713/AI-music-producer/actions/runs/24644826851/job/72055436125",
            "py -3.13 -m pytest -q",
            "bash tools/scripts/run_quality_gates_ci.sh",
        ],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G3 PASS-EVIDENCE PASS" in stdout


def test_cli_docs_alignment_check_reports_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "docs-alignment-check",
            "docs/映月工厂_极简歌词工坊_PRD_v2.0.json",
            "one law.md",
            "目录框架规范.md",
            "out/lyrics.txt",
            "out/style.txt",
            "out/exclude.txt",
        ],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G4 DOCS-ALIGNMENT PASS" in stdout


def test_cli_hook_check_g5_reports_pass() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "hook-check", "g5"],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G5 HOOK-CHECK PASS" in stdout


def test_cli_ci_gate_check_g6_reports_pass() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "ci-gate-check", "g6"],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G6 CI-GATE PASS" in stdout


def test_cli_gate_check_all_reports_pass() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "gate-check", "--all"],
        capture_output=True,
        text=False,
        check=False,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G7 TOTAL-CLOSURE PASS" in stdout
    assert "G0=pass" in stdout
    assert "G1=pass" in stdout
    assert "G6=pass" in stdout
