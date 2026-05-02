PROMPT = (
    "对照 brief 检查并最小改动修复，保持段落结构不变。\n"
    "brief:\n{brief}\n歌词:\n{lyrics}\n"
    "Q1 central_image 是否作为情感线索自然出现 不数次数 只判承载感情。\n"
    "Q2 Chorus 第1行或最后1行是否是 hook 逐字 如否就替换 Chorus 第1行 不是插入新行。\n"
    "Q3 V1/V2/C/B 情绪推进是否成立 不成立就改最弱段。\n"
    "Q4 检查每行反物理常识 主语混乱 生造词 并逐行修复最少字。\n"
    "仅输出修改后的完整歌词文本（无 JSON，无任何额外说明）。"
)

SURGICAL = (
    "仅做 surgical_fix：只改最少行来满足 brief，未命中行一字不动。\n"
    "brief:\n{brief}\n歌词:\n{lyrics}\n"
    "检查每行反物理常识 主语混乱 生造词 如夜色吹 后视镜看座椅 直线拉昨夜。\n"
    "优先修 hook未落在Chorus头尾 段落结构超限 标点超限 超长行 反物理句。\n"
    "仅输出修改后的完整歌词文本（无 JSON，无任何额外说明）。"
)
