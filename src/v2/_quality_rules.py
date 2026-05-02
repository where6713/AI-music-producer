import re

PUNC = re.compile(r"[,.!?;:，。！？；：、]")
WORD = re.compile(r"[A-Za-z]{2,}")


def check(text: str) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("["):
            continue
        if PUNC.search(s):
            hard.append("punctuation_violation")
            break
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("["):
            continue
        if len(s) > 10:
            hard.append("line_too_long")
            break
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("["):
            continue
        if WORD.search(s):
            hard.append("cn_en_mix")
            break
    return hard, []
