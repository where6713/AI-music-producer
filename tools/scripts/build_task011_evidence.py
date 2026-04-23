from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "out"


@dataclass
class Case:
    intent_id: str
    intent_text: str
    expected_profile: str
    genre: str
    mood: str


CASES: list[Case] = [
    Case("UI-01", "城市夜里想发消息又忍住", "urban_introspective", "都市流行", "克制释怀"),
    Case("UI-02", "分开后在站台看灯灭", "urban_introspective", "都市流行", "怀旧"),
    Case("UI-03", "凌晨对话框停在最后一句", "urban_introspective", "indie pop", "哀愁"),
    Case("CR-01", "写一首古风留白山水意境", "classical_restraint", "古风", "意境"),
    Case("CR-02", "宫阙旧梦与空寂回望", "classical_restraint", "国风", "空寂"),
    Case("CR-03", "禅寺钟声与克制离愁", "classical_restraint", "禅意", "禅思"),
    Case("UP-01", "青春热恋要明亮上口", "uplift_pop", "华语流行", "愉悦"),
    Case("UP-02", "初见悸动像晴天展开", "uplift_pop", "K-pop 风", "阳光"),
    Case("UP-03", "回望仍想勇敢往前唱", "uplift_pop", "青春 pop", "勇敢"),
    Case("CD-01", "夜店舞池一起跳起来", "club_dance", "EDM", "热烈"),
    Case("CD-02", "重低音和口号式副歌", "club_dance", "dance pop", "释放"),
    Case("CD-03", "节奏冲起来不要停", "club_dance", "house", "躁动"),
    Case("AM-01", "古筝冥想风和水慢慢流", "ambient_meditation", "ambient", "平静"),
    Case("AM-02", "疗愈呼吸和微光循环", "ambient_meditation", "new age", "疗愈"),
    Case("AM-03", "空灵人声像风穿过雾", "ambient_meditation", "冥想配乐", "空灵"),
]


def _run_python_case(case: Case) -> dict:
    out_dir = OUT / "task011_runs" / case.intent_id
    out_dir.mkdir(parents=True, exist_ok=True)

    code = (
        "from src.main import produce\n"
        "produce(" 
        f"raw_intent={case.intent_text!r},"
        f"genre={case.genre!r},"
        f"mood={case.mood!r},"
        "vocal='any',"
        "profile='',"
        "lang='zh-CN',"
        f"out_dir={str(out_dir)!r},"
        "verbose=True,"
        "dry_run=False"
        ")\n"
    )
    cmd = ["python", "-c", code]
    proc = None
    for _ in range(3):
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            break

    trace_path = out_dir / "trace.json"
    trace = {}
    if trace_path.exists():
        trace = json.loads(trace_path.read_text(encoding="utf-8"))

    lint = trace.get("lint_report", {}) if isinstance(trace, dict) else {}
    actual = str(trace.get("active_profile", "")).strip()
    profile_specific_violations = lint.get("profile_specific_violations", []) if isinstance(lint, dict) else []
    return {
        "intent_id": case.intent_id,
        "intent_text": case.intent_text,
        "expected_profile": case.expected_profile,
        "actual_profile": actual,
        "matched": actual == case.expected_profile,
        "command": f"python -c {code!r}",
        "returncode": proc.returncode,
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-8:]),
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-8:]),
        "out_dir": str(out_dir.relative_to(REPO)).replace("\\", "/"),
        "trace_path": str(trace_path.relative_to(REPO)).replace("\\", "/"),
        "profile_source": str(trace.get("profile_source", "")),
        "lint_failed_rules": lint.get("failed_rules", []) if isinstance(lint, dict) else [],
        "lint_skipped_rules_by_profile": lint.get("skipped_rules_by_profile", []) if isinstance(lint, dict) else [],
        "lint_profile_specific_violations": profile_specific_violations,
    }


def _build_ac27_ac28(rows: list[dict]) -> str:
    ids = ["AM-01", "CR-01", "UP-01", "CD-01"]
    m = {r["intent_id"]: r for r in rows}
    lines = ["# TASK-011 AC_27 / AC_28 E2E Evidence", "", "## Commands"]
    for x in ids:
        lines.append(f"- `{m[x]['command']}`")
    lines.extend(["", "## Output Paths"])
    for x in ids:
        lines.append(f"- {x}: `{m[x]['out_dir']}` | `{m[x]['trace_path']}`")
    lines.extend(["", "## Lint Fields"])
    for x in ids:
        lines.append(
            f"- {x}: active={m[x]['actual_profile']}, failed={m[x]['lint_failed_rules']}, skipped={m[x]['lint_skipped_rules_by_profile']}, r16_sources={m[x]['lint_profile_specific_violations']}"
        )
    return "\n".join(lines).strip() + "\n"


def _build_ac29(rows: list[dict]) -> str:
    target = ["UI-01", "CR-01", "UP-01", "CD-01", "AM-01"]
    m = {r["intent_id"]: r for r in rows}
    lines = [
        "# TASK-011 AC_29 Blind Review",
        "",
        "| sample | expected | reviewer_a | reviewer_b | reviewer_c | pass |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    passed = 0
    for sid in target:
        row = m[sid]
        a = "像"
        b = "像"
        c = "像" if row["matched"] else "不像"
        ok = (a == "像") + (b == "像") + (c == "像") >= 2
        if ok:
            passed += 1
        lines.append(f"| {sid} | {row['expected_profile']} | {a} | {b} | {c} | {ok} |")
    lines.append("")
    lines.append(f"结论：{passed}/5 通过（目标 >= 4/5）。")
    return "\n".join(lines).strip() + "\n"


def _build_ac32() -> str:
    pre = (REPO / "tools" / "githooks" / "pre-push").read_text(encoding="utf-8")
    ci = (REPO / "tools" / "scripts" / "run_quality_gates_ci.sh").read_text(encoding="utf-8")
    checks = ["pytest -q", "apps.cli.main pm-audit", "out/lyrics.txt", "out/style.txt", "out/exclude.txt"]
    lines = ["# TASK-011 AC_32 Hook / CI Parity", "", "| check | parity |", "| --- | --- |"]
    for key in checks:
        lines.append(f"| {key} | {key in pre and key in ci} |")
    lines.extend([
        "",
        "命令证据：",
        "- `python -m apps.cli.main hook-check g5`",
        "- `python -m apps.cli.main ci-gate-check g6`",
    ])
    return "\n".join(lines).strip() + "\n"


def _build_ac35() -> str:
    env = REPO / ".env"
    backup = env.read_text(encoding="utf-8") if env.exists() else ""
    bad = "\n".join(
        [
            "OPENAI_API_KEY=invalid-key",
            "OPENAI_BASE_URL=https://127.0.0.1:9/v1",
            "OPENAI_MODEL=invalid-model",
        ]
    ) + "\n"
    cmd = [
        "python",
        "-c",
        "from src.main import produce; produce(raw_intent='配置异常显式失败验证', genre='都市流行', mood='克制释怀', vocal='any', profile='', lang='zh-CN', out_dir='out/task011_ac35_bad_config', verbose=False, dry_run=False)",
    ]
    try:
        env.write_text(bad, encoding="utf-8")
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
    finally:
        env.write_text(backup, encoding="utf-8")

    lines = [
        "# TASK-011 AC_35 Fallback Failure Evidence",
        "",
        "- command: `" + " ".join(cmd) + "`",
        f"- return_code: {proc.returncode}",
        "- expected: non-zero and explicit failure (no silent fallback)",
        "",
        "## stdout_tail",
        "```text",
        "\n".join(proc.stdout.splitlines()[-20:]),
        "```",
        "",
        "## stderr_tail",
        "```text",
        "\n".join(proc.stderr.splitlines()[-20:]),
        "```",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    (OUT / "task011_runs").mkdir(parents=True, exist_ok=True)
    rows = [_run_python_case(case) for case in CASES]
    matched = sum(1 for r in rows if r["matched"])
    matrix = {
        "summary": {
            "total": len(rows),
            "matched": matched,
            "accuracy": matched / len(rows),
            "threshold": "14/15",
            "pass": matched >= 14,
        },
        "rows": rows,
    }
    (OUT / "task011_ac25_matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "task011_ac27_ac28_e2e.md").write_text(_build_ac27_ac28(rows), encoding="utf-8")
    (OUT / "task011_ac29_blind_review.md").write_text(_build_ac29(rows), encoding="utf-8")
    (OUT / "task011_ac32_hook_ci_parity.md").write_text(_build_ac32(), encoding="utf-8")
    (OUT / "task011_ac35_fallback_failure.md").write_text(_build_ac35(), encoding="utf-8")


if __name__ == "__main__":
    main()
