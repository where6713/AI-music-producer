import re

SYNTAX_CRUTCH_PATTERNS = [r"我把", r"[\u4e00-\u9fff]把.{1,8}(吹|折|留|放|藏|变|染|带|送|说)", r"让.{1,8}成为", r"把.{1,8}留给", r"在.{1,4}的尽头", r"把.{1,6}[酿写熬折化煮绣拧埋].{0,4}成"]
VISUAL_PROP = ["仪表盘", "路肩", "抬杆", "护栏", "后视镜", "雨刮", "副驾", "油门"]
CLICHE_WORDS = ["站台", "晚安", "风", "海", "星空", "孤单", "思念", "回忆", "眼泪", "时光"]
_CN_EN_MIX = re.compile(r"[\u4e00-\u9fff].*[a-zA-Z]{3,}|[a-zA-Z]{3,}.*[\u4e00-\u9fff]")
_ORPHAN = re.compile(r"^(沉默|回忆|脚步|心事|夜色|天亮).*(折进|留给|带走|藏起|变成|染上)")
_HOOK = re.compile(r"(?m)^\[Chorus\]\n(.{11,})")


def check(text: str) -> list[str]:
    violations: list[str] = []
    if sum(text.count(x) for x in ["啊", "呢", "吧", "呀", "喔", "哦", "呐"]) > 3:
        violations.append("ngram_density")
    for p in SYNTAX_CRUTCH_PATTERNS:
        if re.search(p, text):
            violations.append(f"syntax_crutch:{p}")
    for w in VISUAL_PROP:
        if w in text:
            violations.append(f"blacklist:{w}")
    if _CN_EN_MIX.search(text):
        violations.append("cn_en_mix")
    for ln in [x.strip() for x in text.splitlines() if x.strip() and not x.strip().startswith("[")]:
        if _ORPHAN.search(ln):
            violations.append("orphan_subject")
            break
    counts = {w: text.count(w) for w in CLICHE_WORDS}
    total = sum(1 for c in counts.values() if c > 0)
    if total >= 3:
        violations.append(f"cliche_density:total={total}")
    cooccur = sum(1 for i, w1 in enumerate(CLICHE_WORDS) for w2 in CLICHE_WORDS[i + 1 :] if counts[w1] >= 1 and counts[w2] >= 1)
    if cooccur >= 1:
        violations.append("cliche_cooccurrence")
    h = _HOOK.search(text)
    if h and len(h.group(1).strip()) > 10:
        violations.append("hook_too_long")
    return violations
