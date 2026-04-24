from __future__ import annotations

from pathlib import Path

from src.producer_tools.self_check import gate_g0


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ok\n", encoding="utf-8")


def test_check_gate_g0_pass_with_required_docs_and_hooks(monkeypatch, tmp_path: Path) -> None:
    hooks_dir = tmp_path / "tools" / "githooks"
    for hook in gate_g0.REQUIRED_HOOKS:
        _touch(hooks_dir / hook)

    for rel in gate_g0.REQUIRED_DOCS:
        _touch(tmp_path / rel)

    monkeypatch.setattr(gate_g0, "_read_hooks_path", lambda _: "tools/githooks")
    result = gate_g0.check_gate_g0(tmp_path)

    assert result["status"] == "pass"
    assert result["missing_hooks"] == []
    assert result["missing_docs"] == []


def test_check_gate_g0_fail_when_required_doc_missing(monkeypatch, tmp_path: Path) -> None:
    hooks_dir = tmp_path / "tools" / "githooks"
    for hook in gate_g0.REQUIRED_HOOKS:
        _touch(hooks_dir / hook)

    _touch(tmp_path / "one law.md")
    _touch(tmp_path / "docs" / "ai_doc_manifest.json")

    monkeypatch.setattr(gate_g0, "_read_hooks_path", lambda _: "tools/githooks")
    result = gate_g0.check_gate_g0(tmp_path)

    assert result["status"] == "fail"
    assert "docs/映月工厂_极简歌词工坊_PRD.json" in result["missing_docs"]
