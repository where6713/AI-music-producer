import re

BA_VERBS = "酿|熬|绣|捏|拧|埋"
BA_PATTERN = re.compile(rf"把.{{1,8}}({BA_VERBS}).{{0,4}}成")
BA_I_PATTERN = re.compile(r"(?m)^我把")
SYNTAX = [r"让.{1,8}成为", r"把.{1,8}留给", r"在.{1,4}的尽头"]
VISUAL = ["仪表盘", "路肩", "抬杆", "护栏", "后视镜", "雨刮", "副驾", "油门"]
CLICHE = ["站台", "晚安", "风", "海", "星空", "孤单", "思念", "回忆", "眼泪", "时光"]
CN_EN = re.compile(r"[\u4e00-\u9fff].*[a-zA-Z]{3,}|[a-zA-Z]{3,}.*[\u4e00-\u9fff]")
ORPHAN = re.compile(r"^(沉默|回忆|脚步|心事|夜色|天亮).*(折进|留给|带走|藏起|变成|染上)")
HOOK = re.compile(r"(?m)^\[Chorus\]\n(.{11,})")
