from __future__ import annotations

import shutil
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
CLI = [PYTHON, "-m", "apps.cli.main"]

PROFILES = [
    "urban_introspective",
    "classical_restraint",
    "uplift_pop",
    "club_dance",
    "ambient_meditation",
]

REALISTIC_INTENTS = {
    "urban_introspective": "分手后夜里想发消息又忍住",
    "classical_restraint": "古寺钟声远，落叶满空山",
    "uplift_pop": "第一次约会时的紧张和期待",
    "club_dance": "舞池里放下一切尽情释放",
    "ambient_meditation": "清晨海边听浪，内心逐渐平静",
}


def _run_profile(
    profile: str,
    out_dir: Path,
    *,
    dry_run: bool = True,
    expect_fail: bool = False,
    retries: int = 2,
) -> subprocess.CompletedProcess:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Use relative path for --out-dir to avoid absolute path issues
    rel_out_dir = out_dir.relative_to(REPO_ROOT)
    cmd = [
        *CLI,
        "produce",
        REALISTIC_INTENTS[profile],
        "--profile",
        profile,
        "--out-dir",
        str(rel_out_dir),
        "--lang",
        "zh-CN",
    ]
    if dry_run:
        cmd.append("--dry-run")
    env = dict(os.environ)
    if dry_run:
        env["LYRIC_DRY_RUN_FAST"] = "1"

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
    if result.returncode != 0 and retries > 0 and not expect_fail:
        # Clean up and retry on failure to handle flaky LLM generation
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        return _run_profile(profile, out_dir, dry_run=dry_run, expect_fail=expect_fail, retries=retries - 1)
    if expect_fail:
        assert result.returncode == 2, (
            f"Expected exit code 2, got {result.returncode} for profile={profile}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def _assert_isolated(out_dir: Path, profile: str) -> None:
    trace_path = out_dir / "trace.json"
    assert trace_path.exists(), f"trace.json missing in {out_dir}"
    trace = __import__("json").loads(trace_path.read_text(encoding="utf-8"))
    assert trace.get("active_profile") == profile, (
        f"Profile mismatch in {out_dir}: expected {profile}, got {trace.get('active_profile')}"
    )


def _assert_dry_run_ok(result: subprocess.CompletedProcess, profile: str, out_dir: Path) -> None:
    assert result.returncode == 0, (
        f"Profile {profile} failed with exit code {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    combined = (result.stdout + "\n" + result.stderr).lower()
    assert "dry-run complete" in combined, f"Missing dry-run marker for {profile}: {combined}"
    # dry-run should not write output artifacts; this keeps test fast and deterministic
    assert not (out_dir / "trace.json").exists(), f"dry-run unexpectedly wrote trace.json for {profile}"


@pytest.fixture(autouse=True)
def _cleanup_test_out_dirs():
    yield
    test_out = REPO_ROOT / "out"
    if test_out.exists():
        for item in test_out.iterdir():
            if item.is_dir() and item.name.startswith("test_"):
                shutil.rmtree(item, ignore_errors=True)


def test_all_profiles_sequential() -> None:
    if os.environ.get("RUN_E2E_LIVE", "0") != "1":
        pytest.skip("Set RUN_E2E_LIVE=1 to run live sequential profile E2E")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, profile in enumerate(PROFILES):
        out_dir = REPO_ROOT / "out" / f"test_{profile}_{timestamp}_{i:03d}"
        result = _run_profile(profile, out_dir, dry_run=True)
        _assert_dry_run_ok(result, profile, out_dir)


def test_all_profiles_concurrent() -> None:
    if os.environ.get("RUN_E2E_LIVE", "0") != "1":
        pytest.skip("Set RUN_E2E_LIVE=1 to run live concurrent profile E2E")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dirs: list[tuple[str, Path]] = []
    for i, profile in enumerate(PROFILES):
        out_dir = REPO_ROOT / "out" / f"test_{profile}_{timestamp}_concurrent_{i:03d}"
        out_dirs.append((profile, out_dir))

    with ThreadPoolExecutor(max_workers=len(PROFILES)) as executor:
        futures = {
            executor.submit(_run_profile, profile, out_dir, dry_run=True): (profile, out_dir)
            for profile, out_dir in out_dirs
        }
        for future in as_completed(futures):
            profile, out_dir = futures[future]
            result = future.result()
            _assert_dry_run_ok(result, profile, out_dir)


def test_dirty_directory_rejected() -> None:
    out_dir = REPO_ROOT / "out" / "test_dirty_rejected"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trace.json").write_text('{"run_status":"EXISTING"}', encoding="utf-8")

    result = _run_profile(PROFILES[0], out_dir, dry_run=False, expect_fail=True)
    assert "already contains trace.json" in (result.stderr + result.stdout)
