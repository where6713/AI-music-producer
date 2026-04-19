# PM_AUDIT_REPORT

[PASS] E2E 全链路复测达标（得分 9.3/10）

## 本次真实运行
- run_dir: `.tmp/pm-real-e2e-20260419-pmfix-1/`
- run_id / trace_id: `647a83976463df94`
- 真实资产:
  - `F:/Onedrive/桌面/Dancing with my phone - HYBS.flac`
  - `F:/Onedrive/桌面/干音模板.mp3`

## P0 打勾情况
- [x] P0-1 根目录交付物：`OUTPUT_DEMO_PROMPT.md` / `PM_AUDIT_REPORT.md`
- [x] P0-2 Style Box 五维 + 4-7 标签 + 无互斥
- [x] P0-3 Lyrics Box 控制码：`[Energy: High]` / `[Build-up]` + 动态气口 + 具象名词 + 开口音门禁
- [x] P0-4 四类审计日志 + Chaos 阻断日志
- [x] P0-5 反偷懒探针：真实读取 grids/montage/shisanzhe，失败诊断落盘
- [x] P0-6 三列表映射补全（函数级测试）

## 四类审计日志（同 run_id）
- `[Grid Loaded]` `pattern=4-8-5-11`
- `[Montage Hit]` `selected_entities=[外卖订单,雨点,收银台,...] seed=868764`
- `[Phonetic Check]` `target_char=台 pinyin=tai yunmu=ai zhe=怀来辙 decision=pass`
- `[Cliche Hit]` `reason_code=cliche_density_exceeded decision=rewrite`

## Chaos 阻断日志
- `[Blocked] 触发 cliche_blacklist.json 违禁词，强行阻断并退回重构`

## 验收命令结果
- `py -3.13 -m pytest tests/test_lyric_architect.py tests/test_prompt_compiler.py tests/test_orchestrator.py tests/test_e2e_smoke.py -q`
  - 结果：`90 passed`
- `py -3.13 -m pytest -q`
  - 结果：`232 passed, 1 skipped`

## 自动证据汇总
- `tools/scripts/summarize_e2e_evidence.py`
- 输出：`.tmp/pm-real-e2e-20260419-pmfix-1/evidence_summary.json`
- 摘要：`run_id=647a83976463df94 score=9.3 event_counts(Grid/Montage/Phonetic/Cliche)=144/48/24/8`
