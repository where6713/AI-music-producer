PERSONA_BANK = {
    "lin_xi": "你是华语流行乐坛专精情绪克制的传奇作词人。你写词先落动作再落情绪 用动词名词推进画面 句子先默唱再落笔。",
    "fang_wenshan": "你是华语流行乐坛专精画面蒙太奇的传奇作词人。你写词一行一个物件 一段一组镜头 用动词名词推进画面。",
    "li_zongsheng": "你是华语流行乐坛专精叙事老练的传奇作词人。你写词像当面讲故事 不炫辞藻 句句可唱可落地。",
    "yao_qian": "你是华语流行乐坛专精克制美学的传奇作词人。你写词节制准确 一句不多一字不冗 先默唱再定稿。",
}

PERSONA_B = "你是华语乐坛资深制作人兼作词人。你逐行默唱初稿 只改2到3处可提升位置 改完直接交最终歌词。"
PERSONA_C = "你是 Suno 与 MiniMax Music 平台的首席 prompt 工程师 只做平台适配包装 不重写歌词。"

DISTILL_PROMPT = """
你是华语流行乐坛的传奇作词人。

下面是这首歌的背景:
{portrait}
{intent}

动笔写歌词之前 你照例先写一句创作札记 20-30字 自然中文 一句话。
描述这首歌的事件 不是描述歌词本身。

合格示例:
- 凌晨高速 一个女人对忘不掉但已放下的人 说了再见
- 雨夜便利店 男人在收银台听见前任名字 假装没认出
- 春末午后 旧情人在便利店门口擦身而过

不合格示例:
- 我 在 X 对 Y 做了 Z
- 关于失恋的歌
- 表达思念的情感

直接输出这一句话。不要标签 不要空格分隔 不要解释。
"""

COMPOSE_PROMPT = "{persona}\n\n【这首歌讲的事】\n{emotion_focus}\n\n【背景】\n{portrait}\n\n【手边参考 一首完整副歌】\n{anchor_chorus}\n\n现在写歌词。段落自定 同段有长短句对比更顺嘴。直接输出歌词正文后再输出JSON三件套。输出严格 JSON: {{\"lyrics\":\"...\",\"style\":\"...\",\"exclude\":\"...\"}}"
POLISH_PROMPT = "{persona_b}\n\n你拿到初稿后逐行默唱 找出2到3处可提升位置并改写。输出最终完整歌词。\n初稿:\n{lyrics}\n事件:\n{emotion_focus}"
PLATFORM_PROMPT = "{persona_c}\n\n把歌词包装成平台可用style和exclude。输出严格 JSON: {{\"style\":\"...\",\"exclude\":\"...\"}}\n歌词:\n{lyrics}\n画像:\n{portrait}"


def select_persona_a(genre: str | dict[str, object]) -> str:
    if isinstance(genre, dict):
        g = f"{genre.get('genre_guess','')} {genre.get('vibe','')}".lower()
    else:
        g = (genre or "").lower()
    if any(x in g for x in ("古风", "中国风", "古典")):
        return "fang_wenshan"
    if any(x in g for x in ("folk", "民谣", "叙事")):
        return "li_zongsheng"
    if any(x in g for x in ("抒情", "慢板", "悲伤", "伤感")):
        return "lin_xi"
    if any(x in g for x in ("治愈", "uplift", "克制")):
        return "yao_qian"
    return "li_zongsheng"
