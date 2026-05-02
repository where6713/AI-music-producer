import re

_BA_VERBS = "酿|熬|绣|捏|拧|埋"
_BA_PATTERN = re.compile(rf"把.{{1,8}}({_BA_VERBS}).{{0,4}}成")
_BA_I_PATTERN = re.compile(r"(?m)^我把")
_SYNTAX = [r"让.{1,8}成为", r"把.{1,8}留给", r"在.{1,4}的尽头"]
_VISUAL = ["仪表盘", "路肩", "抬杆", "护栏", "后视镜", "雨刮", "副驾", "油门"]
_CLICHE = ["站台", "晚安", "风", "海", "星空", "孤单", "思念", "回忆", "眼泪", "时光"]
_CN_EN = re.compile(r"[\u4e00-\u9fff].*[a-zA-Z]{3,}|[a-zA-Z]{3,}.*[\u4e00-\u9fff]")
_ORPHAN = re.compile(r"^(沉默|回忆|脚步|心事|夜色|天亮).*(折进|留给|带走|藏起|变成|染上)")
_HOOK = re.compile(r"(?m)^\[Chorus\]\n(.{11,})")


def _ba_density(text: str) -> list[str]:
    ba_i = len(_BA_I_PATTERN.findall(text))
    ba_v = len(_BA_PATTERN.findall(text))
    out: list[str] = []
    if ba_i >= 2:
        out.append("syntax_crutch:ba_i_count")
    if ba_v >= 3:
        out.append("syntax_crutch:ba_v_density")
    return out


def check(text: str) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    if sum(text.count(x) for x in ["啊", "呢", "吧", "呀", "喔", "哦", "呐"]) > 3:
        hard.append("ngram_density")
    for p in _SYNTAX:
        if re.search(p, text):
            hard.append(f"syntax_crutch:{p}")
    hard += _ba_density(text)
    for w in _VISUAL:
        if w in text:
            hard.append(f"blacklist:{w}")
    if _CN_EN.search(text):
        hard.append("cn_en_mix")
    for ln in [x.strip() for x in text.splitlines() if x.strip() and not x.strip().startswith("[")]:
        if _ORPHAN.search(ln):
            hard.append("orphan_subject")
            break
    counts = {w: text.count(w) for w in _CLICHE}
    total = sum(1 for c in counts.values() if c > 0)
    if total >= 3:
        hard.append(f"cliche_density:total={total}")
    cooccur = sum(1 for i, w1 in enumerate(_CLICHE) for w2 in _CLICHE[i + 1:] if counts[w1] >= 1 and counts[w2] >= 1)
    if cooccur >= 1:
        soft.append("cliche_cooccurrence")
    h = _HOOK.search(text)
    if h and len(h.group(1).strip()) > 10:
        hard.append("hook_too_long")
    return hard, soft
