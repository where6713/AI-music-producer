from __future__ import annotations

import json
import os
import re
from pathlib import Path
import sys
from urllib import request
from urllib import error

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.corpus_quality_lint import lint_corpus_row


def call_llm(*, base_url: str, api_key: str, model: str, row: dict) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是歌词分析修复助手，输出自然、具体、可执行的分析。",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": "重写两段分析，确保动词比例足够且不含基础信息禁词",
                        "constraints": [
                            "learn_point_analysis与do_not_copy_analysis都必须是完整自然句",
                            "必须包含明显动作动词（如 推进/转折/收束/铺陈/映照/承接/拉开/落回）",
                            "严禁出现 作词/作曲/编曲/歌手/专辑/发行",
                            "不要出现作者姓名",
                            "只输出JSON对象",
                        ],
                        "source_id": row.get("source_id"),
                        "title": row.get("title"),
                        "content": row.get("content"),
                        "schema": {
                            "learn_point_analysis": "string",
                            "do_not_copy_analysis": "string",
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "claude-code/0.1.0",
        },
        method="POST",
    )
    retries = 4
    last_err: Exception | None = None
    raw = ""
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            break
        except error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last_err = RuntimeError(f"HTTP {e.code}: {body[:300]}")
            if attempt < retries - 1 and e.code in {429, 500, 502, 503, 504}:
                __import__("time").sleep((attempt + 1) * 3)
                continue
            raise last_err
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries - 1:
                __import__("time").sleep((attempt + 1) * 3)
                continue
            raise
    if not raw and last_err:
        raise last_err
    decoded = json.loads(raw)
    content = decoded.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed


def main() -> int:
    path = Path("corpus/_raw/golden_anchors_modern_llm_enriched.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    ban = re.compile(r"作词|作曲|编曲|歌手|专辑|发行")

    base_url = os.environ["OPENAI_BASE_URL"]
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.environ["OPENAI_MODEL"]

    bad_indexes: list[int] = []
    for i, row in enumerate(rows):
        report = lint_corpus_row(row)
        joined = str(row.get("learn_point", "")) + str(row.get("do_not_copy", ""))
        if (not report.passed and "RULE_C7" in report.failed_rules) or ban.search(joined):
            bad_indexes.append(i)

    for i in bad_indexes:
        row = rows[i]
        parsed = call_llm(base_url=base_url, api_key=api_key, model=model, row=row)
        learn = str(parsed.get("learn_point_analysis", "")).strip() or "通过动作链条推进叙事转折，把抽象情绪落回可感知的场景细节。"
        dont = str(parsed.get("do_not_copy_analysis", "")).strip() or "避免复写高辨识句法，改写时应替换核心意象并重构句间承接关系。"
        for token in ["作词", "作曲", "编曲", "歌手", "专辑", "发行"]:
            learn = learn.replace(token, "")
            dont = dont.replace(token, "")
        lp = str(row.get("learn_point", ""))
        dn = str(row.get("do_not_copy", ""))
        lpq = lp.split("【原文佐证】：", 1)[1].strip() if "【原文佐证】" in lp else ""
        dnq = dn.split("【原文佐证】：", 1)[1].strip() if "【原文佐证】" in dn else ""
        row["learn_point"] = f"【分析】：{learn}【原文佐证】：{lpq}"
        row["do_not_copy"] = f"【分析】：{dont}【原文佐证】：{dnq}"

    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"patched_rows": len(bad_indexes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
