from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECTS_DIRNAME = "projects"

GIT_DIRNAME = ".git"
GITIGNORE_FILENAME = ".gitignore"

INTENT_FILENAME = "intent.md"
VOICE_PROFILE_FILENAME = "voice_profile.json"
REFERENCE_DNA_FILENAME = "reference_dna.json"
FRICTION_REPORT_FILENAME = "friction_report.json"
LYRICS_FILENAME = "lyrics.json"
COMPILE_LOG_FILENAME = "compile_log.json"

PROMPTS_DIRNAME = "prompts"

ASSETS_DIRNAME = "assets"
ASSETS_TAKES_DIRNAME = "takes"
ASSETS_MASTERS_DIRNAME = "masters"
ASSETS_STEMS_DIRNAME = "stems"

PRODUCER_STATE_FILENAME = ".producer_state.sqlite"

JSON_ARTIFACT_FILENAMES = (
    VOICE_PROFILE_FILENAME,
    REFERENCE_DNA_FILENAME,
    FRICTION_REPORT_FILENAME,
    LYRICS_FILENAME,
    COMPILE_LOG_FILENAME,
)


@dataclass(frozen=True)
class ProjectPaths:
    project_dir: Path
    git_dir: Path
    gitignore: Path
    intent: Path
    voice_profile: Path
    reference_dna: Path
    friction_report: Path
    lyrics: Path
    compile_log: Path
    prompts_dir: Path
    assets_dir: Path
    takes_dir: Path
    masters_dir: Path
    stems_dir: Path
    producer_state_db: Path


def project_slug(date: str, name: str) -> str:
    return f"{date}_{name}"


def project_paths(repo_root: Path, slug: str) -> ProjectPaths:
    project_dir = repo_root / PROJECTS_DIRNAME / slug
    assets_dir = project_dir / ASSETS_DIRNAME

    return ProjectPaths(
        project_dir=project_dir,
        git_dir=project_dir / GIT_DIRNAME,
        gitignore=project_dir / GITIGNORE_FILENAME,
        intent=project_dir / INTENT_FILENAME,
        voice_profile=project_dir / VOICE_PROFILE_FILENAME,
        reference_dna=project_dir / REFERENCE_DNA_FILENAME,
        friction_report=project_dir / FRICTION_REPORT_FILENAME,
        lyrics=project_dir / LYRICS_FILENAME,
        compile_log=project_dir / COMPILE_LOG_FILENAME,
        prompts_dir=project_dir / PROMPTS_DIRNAME,
        assets_dir=assets_dir,
        takes_dir=assets_dir / ASSETS_TAKES_DIRNAME,
        masters_dir=assets_dir / ASSETS_MASTERS_DIRNAME,
        stems_dir=assets_dir / ASSETS_STEMS_DIRNAME,
        producer_state_db=project_dir / PRODUCER_STATE_FILENAME,
    )
