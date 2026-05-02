from __future__ import annotations
import json, re
from .llm_runtime import call as llm_call

_PROMPT = (
    "你是创意Brief生成器。先做立意诊断再输出。\n"
    "在生成 brief 前，先做3个判断：\n"
    "1) 这首歌的根是什么？必须用1个具体物件/场景指出来\n"
    "2) 听完能记住哪1句？必须是认知洞察，不是情绪宣泄\n"
    "3) 三段verse情绪不能一样，要像3张照片不是3张副本\n"
    "意图：{intent}\n风格画像：{portrait}\n"
    "只输出中文，不允许英文词；歌手名或英文歌名可保留。\n"
    "【central_image 必须是情感转喻物 不是地理坐标】\n"
    "合格: 红豆 旧伞 票根 冷汤 空座\n"
    "不合格: 收费站 高架 匝道 路口 加油站 ETC 导航 方向盘\n"
    "判定: <=4字 可触摸 可承载感情 如不合格就重选\n"
    "central_image：具体物件名词 仅一个 <=4字 禁地理建筑与设备词。\n"
    "cognitive_hook：一句认知洞察，<=8字，必须是陈述句或祈使句，禁止疑问句和半句话。\n"
    "cognitive_hook 不是装饰 它就是 Chorus 第1行 且会在 Chorus 再重复一次。\n"
    "生成时自问: 这句能不能当歌名 能不能撑起整段副歌押韵 不能就重写。\n"
    "arc_3_stations：3个递进状态，格式如['否认-装没事','承认-痛被看见','放过-不再追问']。\n"
    "输出严格 JSON（无 markdown，无注释）：\n"
    '{{"central_image":"...","cognitive_hook":"...","arc_3_stations":["...","...","..."]}}'
)

def distill_emotion(intent: str, portrait: dict[str, object]) -> dict[str, object]:
    prompt = _PROMPT.format(intent=intent or "", portrait=json.dumps(portrait, ensure_ascii=False))
    content, llm_meta = llm_call(prompt, temperature=0.3)
    s = re.sub(r'^```(?:json)?\s*', '', content.strip())
    s = re.sub(r'\s*```$', '', s)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        i, j = s.find('{'), s.rfind('}')
        if i == -1 or j == -1:
            raise RuntimeError(f"distill_emotion: non-JSON from LLM: {s[:200]}")
        data = json.loads(s[i:j + 1])
    geo = ("收费站", "高架", "服务区", "隧道", "匝道", "桥", "路口", "加油站", "ETC", "导航", "仪表盘", "方向盘")
    data.setdefault("central_image", "票根")
    data.setdefault("cognitive_hook", "我先睡了")
    data.setdefault("arc_3_stations", ["否认-装没事", "承认-痛被看见", "放过-不再追问"])
    image = str(data.get("central_image", "")).strip()
    hook = str(data.get("cognitive_hook", "")).strip()
    if len(image) > 4 or any(x in image for x in geo):
        raise RuntimeError(f"distill_emotion: invalid central_image: {image}")
    if len(hook) > 8 or hook.endswith(("吗", "呢", "吧", "？", "?")):
        data["cognitive_hook"] = "我先睡了"
    data["_llm_meta"] = [llm_meta]
    return data
