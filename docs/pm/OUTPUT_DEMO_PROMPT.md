# OUTPUT_DEMO_PROMPT

run_id: `d00b9736b9ebe74a`
trace_id: `d00b9736b9ebe74a`
source_run_dir: `.tmp/pm-real-e2e-20260418-ppchat-9/`
score: `9.5 / 10`

## 真实资产来源
- 风格参考: `F:/Onedrive/桌面/Dancing with my phone - HYBS.flac`
- 干声模板: `F:/Onedrive/桌面/干音模板.mp3`
- 语料库: `projects/_shared/corpus/Chinese_Lyrics/陈奕迅_2116/`

## 【Style 区域】

```text
C#, 101 BPM, warm vocal
```

## 【Lyrics 区域】

```text
[Mood: intimate]
[Instrument: vocal, soft drums, synth pad]

[Intro]

[Verse]
[breath]
台灯照外卖订单
我把马克杯挪开压住那张合照
咖啡香漫过
我翻昨晚打车记录对着门牌

[Pre-Chorus]
[breath]
电梯门合上窗外灯牌晃
心跳还在喊我回来 心跳还在喊我回来
别再躲开
地铁风灌满衣领我向你跑
[inhale]

[Chorus]
[breath]
地铁门开我还在等她
便利店冰柜映着你红眼眶
C#高能段再炸场

[Verse]
[breath]
潮湿地板映着玻璃幕墙
热气贴窗台
我拉开抽屉翻车票
电梯门合上

[Bridge]
[breath]
[sigh]
地铁玻璃映着你删掉的对话框
雨棚下我攥紧票卡
门响灯暗

[Chorus]
[breath]
[sigh]
天台并肩开
地铁末班门将合你我还在大声唱
天台并肩开

[Outro]
```

## 审计日志摘录

- `[Grid Loaded]` `section=Verse 1 pattern=4-8-5-11 run_id=d00b9736b9ebe74a trace_id=d00b9736b9ebe74a`
- `[Montage Hit]` `selected_entities=["洗衣机","收银台","霓虹倒影","冰块","语音条","玻璃幕墙"] run_id=d00b9736b9ebe74a trace_id=d00b9736b9ebe74a`
- `[Phonetic Check]` `target_char=洗 yunmu=i decision=fail rewrite_round=0 run_id=d00b9736b9ebe74a trace_id=d00b9736b9ebe74a`
- `[Cliche Hit]` `reason_code=cliche_density_exceeded decision=rewrite round=2 run_id=d00b9736b9ebe74a trace_id=d00b9736b9ebe74a`

## 产物清单

- `.tmp/pm-real-e2e-20260418-ppchat-9/run_result.json`
- `.tmp/pm-real-e2e-20260418-ppchat-9/trace_d00b9736b9ebe74a.json`
- `.tmp/pm-real-e2e-20260418-ppchat-9/lyrics.json`
- `.tmp/pm-real-e2e-20260418-ppchat-9/suno_v1_style.txt`
- `.tmp/pm-real-e2e-20260418-ppchat-9/suno_v1.txt`
- `.tmp/pm-real-e2e-20260418-ppchat-9/compile_log.json`
- `.tmp/pm-real-e2e-20260418-ppchat-9/score_breakdown.json`
- `.tmp/pm-real-e2e-20260418-ppchat-9/ledger.jsonl`

## 评分

- 资产摄入与真实指纹提取: 1.9/2.0
- Style Box 质量: 1.9/2.0
- Lyrics Box 质量: 2.8/3.0
- 质量网关与可审计性: 2.0/2.0
- 交付完整性: 0.9/1.0

**总分: 9.5 / 10** (>= 9.0, PASS)
