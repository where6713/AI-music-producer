from __future__ import annotations

import importlib
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


path_conventions = importlib.import_module("producer_tools.path_conventions")


def test_project_slug_builds_expected_format() -> None:
    slug = path_conventions.project_slug("2026-04-07", "jay_style")
    assert slug == "2026-04-07_jay_style"


def test_project_paths_follow_conventions() -> None:
    repo_root = Path("C:/repo")
    slug = path_conventions.project_slug("2026-04-07", "jay_style")
    paths = path_conventions.project_paths(repo_root, slug)

    project_dir = repo_root / path_conventions.PROJECTS_DIRNAME / slug
    assert paths.project_dir == project_dir
    assert paths.git_dir == project_dir / path_conventions.GIT_DIRNAME
    assert paths.gitignore == project_dir / path_conventions.GITIGNORE_FILENAME
    assert paths.intent == project_dir / path_conventions.INTENT_FILENAME
    assert paths.voice_profile == project_dir / path_conventions.VOICE_PROFILE_FILENAME
    assert paths.reference_dna == project_dir / path_conventions.REFERENCE_DNA_FILENAME
    assert (
        paths.friction_report == project_dir / path_conventions.FRICTION_REPORT_FILENAME
    )
    assert paths.lyrics == project_dir / path_conventions.LYRICS_FILENAME
    assert paths.compile_log == project_dir / path_conventions.COMPILE_LOG_FILENAME
    assert paths.prompts_dir == project_dir / path_conventions.PROMPTS_DIRNAME
    assert paths.assets_dir == project_dir / path_conventions.ASSETS_DIRNAME
    assert paths.takes_dir == paths.assets_dir / path_conventions.ASSETS_TAKES_DIRNAME
    assert (
        paths.masters_dir == paths.assets_dir / path_conventions.ASSETS_MASTERS_DIRNAME
    )
    assert paths.stems_dir == paths.assets_dir / path_conventions.ASSETS_STEMS_DIRNAME
    assert (
        paths.producer_state_db
        == project_dir / path_conventions.PRODUCER_STATE_FILENAME
    )


def test_json_artifacts_listed_for_git_tracking() -> None:
    expected = {
        path_conventions.VOICE_PROFILE_FILENAME,
        path_conventions.REFERENCE_DNA_FILENAME,
        path_conventions.FRICTION_REPORT_FILENAME,
        path_conventions.LYRICS_FILENAME,
        path_conventions.COMPILE_LOG_FILENAME,
    }
    assert expected.issubset(set(path_conventions.JSON_ARTIFACT_FILENAMES))
