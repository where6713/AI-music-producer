# OUTPUT_DEMO_PROMPT

run_id: `647a83976463df94`
trace_id: `647a83976463df94`
source_run_dir: `.tmp/pm-real-e2e-20260419-pmfix-1/`
score: `9.3 / 10`

## 【Style Box】

```text
urban pop, C#, 101 BPM, warm vocal, vocal + soft drums, intimate
```

- 维度映射:
  - Genre/Decade: `urban pop`
  - Tempo(BPM): `101 BPM`
  - Instrumentation(2-3): `vocal + soft drums`
  - Vocal Identity: `warm vocal`
  - Mood(单一): `intimate`

## 【Lyrics Box】

```text
[Mood: intimate]
[Instrument: vocal, soft drums, synth pad]

[Intro]

[Verse]
[breath]
台灯照抽屉
我盯着定位在玻璃反光里晃
夜风掀窗帘
街声压住鞋跟在楼道回响

[Pre-Chorus]
[Energy: High]
[Build-up]
[breath]
地铁玻璃映出你泪光
别再躲开
雨刷刮过高架你喊我回来
回来吧快讲
[inhale]

[Chorus]
[Energy: High]
[Build-up]
[breath]
地铁门开场
便利店灯牌晃到凌晨我还在站
地铁门开场

[Verse]
[breath]
手机屏亮着，打车记录停在夜市口
外卖袋压着汽水
玻璃幕墙反光
我把零钱摊平塞进旧夹层

[Bridge]
[breath]
[sigh]
[whisper]
地铁门夹住雨伞
你按住我肩膀
便利店灯下我们改签机票航班

[Chorus]
[Energy: High]
[Build-up]
[breath]
[sigh]
地铁门开闸
C#高能段重复意象再喊一遍吧
整夜开嗓

[Outro]
```

## 审计日志与阻断日志（同 run_id）

- `[Grid Loaded]` `pattern=4-8-5-11` `run_id=647a83976463df94` `trace_id=647a83976463df94`
- `[Montage Hit]` `selected_entities=[外卖订单,雨点,收银台,潮湿地板,...]` `seed=868764`
- `[Phonetic Check]` `target_char=台 pinyin=tai yunmu=ai zhe=怀来辙 decision=pass`
- `[Cliche Hit]` `reason_code=cliche_density_exceeded decision=rewrite`
- `[Blocked]` `触发 cliche_blacklist.json 违禁词，强行阻断并退回重构`

## 自动汇总证据

- summary: `.tmp/pm-real-e2e-20260419-pmfix-1/evidence_summary.json`
- command: `C:/Python313/python.exe tools/scripts/summarize_e2e_evidence.py .tmp/pm-real-e2e-20260419-pmfix-1`
