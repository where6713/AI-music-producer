from ._persona import PERSONA_C

ADAPT = (
    f"{PERSONA_C}\n\n"
    "把下面歌词包装成平台可用风格描述。"
    "输出严格 JSON: {{\"style\":\"...\",\"exclude\":\"...\"}}\n"
    "歌词:\n{lyrics}\n画像:\n{portrait}\n"
)
