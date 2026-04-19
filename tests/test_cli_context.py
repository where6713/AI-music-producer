import subprocess
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


def test_cli_context_command_outputs_summary() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "context"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip()
    # Fresh repo state may have no notepad context yet.
    assert (
        "LEARNINGS" in result.stdout
        or "No project memory context available." in result.stdout
    )


def test_load_dotenv_if_exists_populates_env(tmp_path: Path, monkeypatch) -> None:
    from apps.cli.main import _load_dotenv_if_exists

    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_BASE_URL=https://code.ppchat.vip/v1\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    _load_dotenv_if_exists()

    import os

    assert os.getenv("OPENAI_BASE_URL") == "https://code.ppchat.vip/v1"
