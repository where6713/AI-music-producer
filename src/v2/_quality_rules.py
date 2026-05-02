import re
from ._quality_rules_data import BA_I_PATTERN, BA_PATTERN, CLICHE, CN_EN, HOOK, ORPHAN, SYNTAX, VISUAL, RHYME_TABLE, ACTION_V, EMOT_V


def _rhyme_rate(s: str) -> float:
    k = [RHYME_TABLE[l.rstrip()[-1]] for l in s.splitlines()
         if l.strip() and l.strip()[0] not in ("[", "#") and l.rstrip() and l.rstrip()[-1] in RHYME_TABLE]
    return (k.count(max(set(k), key=k.count)) / len(k)) if len(k) >= 3 else 1.0


def check(text: str) -> tuple[list[str], list[str]]:
    hard, soft = [], []
    if sum(text.count(x) for x in ["啊", "呢", "吧", "呀", "喔", "哦", "呐"]) > 3:
        hard.append("ngram_density")
    if len(BA_I_PATTERN.findall(text)) >= 2:
        hard.append("syntax_crutch:ba_i_count")
    if len(BA_PATTERN.findall(text)) >= 3:
        hard.append("syntax_crutch:ba_v_density")
    hard += [f"syntax_crutch:{p}" for p in SYNTAX if re.search(p, text)]
    hard += [f"blacklist:{w}" for w in VISUAL if w in text]
    if CN_EN.search(text):
        hard.append("cn_en_mix")
    if any(ORPHAN.search(x.strip()) for x in text.splitlines() if x.strip() and not x.strip().startswith("[")):
        hard.append("orphan_subject")
    counts = {w: text.count(w) for w in CLICHE}
    if sum(1 for c in counts.values() if c > 0) >= 3:
        hard.append("cliche_density")
    if any(counts[w1] >= 1 and counts[w2] >= 1 for i, w1 in enumerate(CLICHE) for w2 in CLICHE[i + 1:]):
        soft.append("cliche_cooccurrence")
    h = HOOK.search(text)
    if h and len(h.group(1).strip()) > 10:
        hard.append("hook_too_long")
    for s in re.split(r"(?=\[(?:Verse|Chorus|Pre-Chorus|Bridge))", text):
        if s.strip() and re.search(r"[\u4e00-\u9fff]", s) and _rhyme_rate(s) < 0.6:
            hard.append("rhyme_scheme_violation"); break
    lns = [l for l in text.splitlines() if l.strip() and not l.strip().startswith("[")]
    if any(all(any(a in lns[j] for a in ACTION_V) and not any(e in lns[j] for e in EMOT_V)
               for j in range(i, i + 3)) for i in range(max(0, len(lns) - 2))):
        hard.append("action_dump_violation")
    return hard, soft
