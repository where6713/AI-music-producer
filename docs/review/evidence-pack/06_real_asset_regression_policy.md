## Real Asset Regression Policy

### Rule
- 每次涉及歌词质量门、prompt 编译、重写策略或审计链路的改动，必须至少保留 1 条真实音频 E2E 回归样本。

### Baseline Sample
- run directory: `.tmp/pm-real-e2e-20260418-ppchat-9/`
- run_id: `d00b9736b9ebe74a`
- assets:
  - `F:/Onedrive/桌面/Dancing with my phone - HYBS.flac`
  - `F:/Onedrive/桌面/干音模板.mp3`

### Required Evidence
- `run_result.json`
- `trace_<run_id>.json`
- `score_breakdown.json`
- `evidence_summary.json`（由 `tools/scripts/summarize_e2e_evidence.py` 生成）

### Verification Command
- `C:/Python313/python.exe tools/scripts/summarize_e2e_evidence.py .tmp/pm-real-e2e-20260418-ppchat-9`

### Acceptance Check
- `evidence_summary.json` 中 `run_id` 与 `trace_id` 必须一致。
- `event_counts` 必须包含四类审计日志：
  - `[Grid Loaded]`
  - `[Montage Hit]`
  - `[Phonetic Check]`
  - `[Cliche Hit]`
- 若任一事件缺失，PR 不得进入 Ready。
