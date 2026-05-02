from ._persona import PERSONA

P1 = (
    f"{PERSONA}\n\n"
    "下面是一首正在制作的歌。\n"
    "【背景】\n{portrait}\n{brief}\n"
    "【手边一份近作】\n{golden}\n"
    "开始吧。Verse 1 / Verse 2 / Chorus / Bridge 各取所需 长短自定。\n"
    "直接给 lyrics + style + exclude 三件套(JSON)。\n"
    "输出严格 JSON: {{\"lyrics\":\"...\",\"style\":\"...\",\"exclude\":\"...\"}}"
)
