from ._persona import PERSONA_BANK

P1 = (
    "{persona}\n\n"
    "下面是一首正在制作的歌。\n"
    "【一句话情感聚焦】\n{emotion_focus}\n\n"
    "【背景】\n{portrait}\n\n"
    "【手边的参考 一首前辈完整副歌】\n{anchor_chorus}\n\n"
    "现在写吧。段落自定 但同段内有长短句对比 5-9字交错更顺嘴。\n"
    "段落标签愿意加 [主歌] [副歌] [桥段] 就加 不愿意就裸写。\n"
    "直接输出歌词正文。\n"
    "输出歌词正文后再输出 JSON 三件套。\n"
    "输出严格 JSON: {{\"lyrics\":\"...\",\"style\":\"...\",\"exclude\":\"...\"}}"
)
