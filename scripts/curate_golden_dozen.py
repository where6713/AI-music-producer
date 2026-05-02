import json
import random
import re
import hashlib
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpus" / "golden_dozen"
CANDIDATES = [
    {"file": "hybs_dancing_with_my_phone.txt", "artist_aliases": ["HYBS"], "title_aliases": ["Dancing with my phone"], "style": "indie pop 慵懒", "texture": "轻口语 / 低叙事密度 / 节拍主导"},
    {"file": "gao_wu_ren_airen_cuo_guo.txt", "artist_aliases": ["告五人", "Accusefive"], "title_aliases": ["爱人错过"], "style": "indie pop 慵懒", "texture": "短句循环 / 情绪反拍"},
    {"file": "deca_joins_hai_lang.txt", "artist_aliases": ["deca joins", "DecaJoins"], "title_aliases": ["海浪"], "style": "indie 松弛", "texture": "留白多 / 画面感漂移"},
    {"file": "chen_yi_xun_k_ge_zhi_wang_mandarin.txt", "artist_aliases": ["陈奕迅", "Eason Chan"], "title_aliases": ["K歌之王"], "style": "慢板抒情(国语版)", "texture": "密集内心独白 / 修辞递进"},
    {"file": "tian_fu_zhen_xiao_xing_yun.txt", "artist_aliases": ["田馥甄", "Hebe"], "title_aliases": ["小幸运"], "style": "慢板抒情", "texture": "朴素叙事 / 情绪收束"},
    {"file": "zhou_jielun_qing_hua_ci.txt", "artist_aliases": ["周杰伦", "Jay Chou"], "title_aliases": ["青花瓷"], "style": "古典中国风", "texture": "古典意象串联 / 文白交织"},
    {"file": "wuyuetian_jue_jiang.txt", "artist_aliases": ["五月天", "Mayday"], "title_aliases": ["倔强"], "style": "摇滚", "texture": "高势能动词 / 群唱口号感"},
    {"file": "zhang_xuan_bao_bei.txt", "artist_aliases": ["张悬", "Deserts Chang"], "title_aliases": ["宝贝", "宝贝(in the night)"], "style": "私语民谣", "texture": "近讲亲密 / 低强度语义推进"},
    {"file": "zhou_jielun_qing_tian.txt", "artist_aliases": ["周杰伦", "Jay Chou"], "title_aliases": ["晴天"], "style": "流行金曲", "texture": "青春叙事 / 旋律友好短句"},
    {"file": "khalil_fong_san_ren_you.txt", "artist_aliases": ["Khalil Fong", "方大同"], "title_aliases": ["三人游"], "style": "R&B", "texture": "律动切分 / 松弛韵尾"},
    {"file": "cai_yi_lin_mei_gui_shao_nian.txt", "artist_aliases": ["蔡依林", "Jolin Tsai"], "title_aliases": ["玫瑰少年", "Womxnly"], "style": "社会议题", "texture": "议题表达 / 抒情平衡"},
    {"file": "lin_jun_jie_xiu_lian_ai_qing.txt", "artist_aliases": ["林俊杰", "JJ Lin"], "title_aliases": ["修炼爱情"], "style": "流行/R&B 过渡", "texture": "情绪推进 / 副歌可唱性"},
]

SLOTS = [
    ("slot01_indie_lazy", ["indie", "慵懒", "lazy", "松弛"], 1),
    ("slot02_slow_ballad", ["抒情", "慢板", "ballad", "悲伤"], 2),
    ("slot03_classical_cn", ["古典", "中国风", "国风", "意象"], 1),
    ("slot04_rock_anthem", ["摇滚", "rock", "群唱", "热血"], 1),
    ("slot05_folk_intimate", ["民谣", "folk", "亲密", "私语"], 1),
    ("slot06_pop_golden", ["流行", "pop", "金曲", "青春"], 2),
    ("slot07_rnb_groove", ["r&b", "律动", "groove", "切分"], 1),
    ("slot08_social_topic", ["议题", "社会", "性别", "身份"], 1),
    ("slot09_uplift", ["uplift", "希望", "治愈", "明亮"], 1),
    ("slot10_introspective", ["内省", "孤独", "夜", "都市"], 1),
]


def _norm(s: str) -> str:
    return str(s).strip().lower()


def _zh_ratio(text: str) -> float:
    if not text:
        return 0.0
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    return zh / max(len(text), 1)


def _write_record(path: Path, source_id: str, style: str, texture: str, body: str) -> None:
    head = (
        f"# source: {source_id}\n"
        f"# style: {style}\n"
        f"# texture: {texture}\n"
        "# version: v0-algorithmic (TODO: TASK-026 替换为人工策展真经典)\n"
    )
    path.write_text(head + body.rstrip() + "\n", encoding="utf-8", newline="\n")


def _run_v0_algorithmic(idx: list[dict], src_rows: dict[str, dict]) -> None:
    random.seed(42)
    for p in OUT.glob("*.txt"):
        p.unlink()
    miss_readme = OUT / "_MISSING.md"
    if miss_readme.exists():
        miss_readme.unlink()
    pool = [
        r for r in idx
        if _zh_ratio(str(r.get("summary_50chars", ""))) >= 0.30
        and 80 <= int(r.get("char_count", 0) or 0) <= 800
        and isinstance(r.get("emotion_tags", []), list)
        and len(r.get("emotion_tags", [])) > 0
    ]
    print(f"readable_pool_size={len(pool)}")
    if len(pool) < 200:
        print("ABORT: readable_pool_size < 200")
        return
    slot_hits: dict[str, int] = {}
    used_ids: set[str] = set()
    total = 0
    for idx_slot, (slot, kws, target) in enumerate(SLOTS, start=1):
        matched = []
        for r in pool:
            rid = str(r.get("id", ""))
            if rid in used_ids:
                continue
            tags = " ".join(str(x) for x in r.get("emotion_tags", [])).lower()
            text = f"{r.get('title','')} {r.get('summary_50chars','')}".lower()
            if any(k.lower() in tags or k.lower() in text for k in kws):
                matched.append(r)
        if slot == "slot01_indie_lazy" and not matched:
            for r in pool:
                rid = str(r.get("id", ""))
                if rid in used_ids:
                    continue
                text = f"{r.get('title','')} {r.get('summary_50chars','')} {' '.join(r.get('emotion_tags', []) or [])}".lower()
                if any(k in text for k in ("夜", "chill", "lofi", "慵懒", "松弛", "bedroom", "mid")):
                    matched.append(r)
        random.shuffle(matched)
        selected = matched[:target]
        slot_hits[slot] = len(selected)
        for r in selected:
            rid = str(r.get("id", ""))
            row = src_rows.get(rid)
            if not row:
                continue
            used_ids.add(rid)
            total += 1
            digest = hashlib.sha256(rid.encode("utf-8", errors="ignore")).hexdigest()[:8]
            out_name = f"slot{idx_slot:02d}_{slot.split('_', 1)[1]}_{digest}.txt"
            texture = ", ".join(str(x) for x in row.get("emotion_tags", [])[:8])
            _write_record(OUT / out_name, rid, slot.replace("slot", "", 1), texture, str(row.get("content", "")))
    (OUT / "_README.md").write_text(
        "# golden_dozen v0\n\n"
        "本目录为 TASK-022 Step2 的算法策展临时占位。\n"
        "不得将本目录内容视作人工核验后的经典曲目原文。\n"
        "后续由 TASK-026 用人工策展真经典替换。\n",
        encoding="utf-8",
    )
    print(f"slot_hits={json.dumps(slot_hits, ensure_ascii=False)}")
    print(f"hit={total} / miss={12-total} / total=12")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="classic", choices=["classic", "v0-algorithmic"])
    ns = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    idx = json.loads((ROOT / "corpus" / "_index.json").read_text(encoding="utf-8"))
    src_rows = {}
    for p in sorted((ROOT / "corpus" / "_clean").glob("*.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            if isinstance(r, dict) and r.get("source_id") and r.get("content"):
                src_rows[str(r["source_id"])] = r
    if ns.mode == "v0-algorithmic":
        _run_v0_algorithmic(idx, src_rows)
        return
    miss = []
    hit = 0
    for c in CANDIDATES:
        pool = [r for r in idx if any(_norm(a) in _norm(r.get("author", "")) for a in c["artist_aliases"]) and any(_norm(t) in _norm(r.get("title", "")) for t in c["title_aliases"]) ]
        if not pool:
            miss.append(f"- {c['file']}: {c['artist_aliases'][0]} - {c['title_aliases'][0]}")
            continue
        best = sorted(pool, key=lambda x: int(x.get("char_count", 0) or 0), reverse=True)[0]
        src = str(best.get("id", ""))
        row = src_rows.get(src)
        if not row:
            miss.append(f"- {c['file']}: {c['artist_aliases'][0]} - {c['title_aliases'][0]}")
            continue
        body = str(row.get("content", "")).rstrip() + "\n"
        head = f"# source: {src}\n# style: {c['style']}\n# texture: {c['texture']}\n"
        (OUT / c["file"]).write_text(head + body, encoding="utf-8", newline="\n")
        hit += 1
    if miss:
        (OUT / "_MISSING.md").write_text("## 未在 _clean/ 命中,需后续人工补 (禁止 LLM 凭记忆生成)\n" + "\n".join(miss) + "\n", encoding="utf-8")
    print(f"hit={hit} / miss={len(miss)} / total=12")
    if miss:
        print("missing:")
        print("\n".join(miss))


if __name__ == "__main__":
    main()
