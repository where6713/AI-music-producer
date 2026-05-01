import re

SYNTAX_CRUTCH_PATTERNS = [r"我把", r"让.{1,8}成为", r"把.{1,8}留给", r"在.{1,4}的尽头"]
CLICHE_WORDS = ["站台", "晚安", "风", "海", "星空", "孤单", "思念", "回忆", "眼泪", "时光"]
_CN_EN_MIX = re.compile(r"[\u4e00-\u9fff].*[a-zA-Z]{3,}|[a-zA-Z]{3,}.*[\u4e00-\u9fff]")


def check(text: str) -> list[str]:
    violations: list[str] = []
    for p in SYNTAX_CRUTCH_PATTERNS:
        if re.search(p, text):
            violations.append(f"syntax_crutch:{p}")
    if _CN_EN_MIX.search(text):
        violations.append("cn_en_mix")
    counts = {w: text.count(w) for w in CLICHE_WORDS}
    total = sum(1 for c in counts.values() if c > 0)
    if total >= 3:
        violations.append(f"cliche_density:total={total}")
    cooccur = sum(1 for i, w1 in enumerate(CLICHE_WORDS) for w2 in CLICHE_WORDS[i + 1 :] if counts[w1] >= 2 and counts[w2] >= 2)
    if cooccur >= 1:
        violations.append("cliche_cooccurrence")
    return violations
