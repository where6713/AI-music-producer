# Issue20 PM Audit Evidence

- Branch: `feature/issue20-style-vocab-control`
- Target: clear quality gate before PR push

## Commands

```bash
python -m apps.cli.main produce "把号码放下吧，电车到站你没回头" --profile urban_introspective
python -m apps.cli.main pm-audit
```

## PM Audit Result

- chosen_variant_not_dead: PASS
- craft_score_floor: PASS (`craft_score=0.8709677419354839`)
- r14_r16_global_hits: PASS
- few_shot_no_numeric_ids: PASS
- audit_sections_complete: PASS
- lyrics_no_residuals: PASS
- postprocess_symbols_absent: PASS
- profile_source_recorded: PASS (`cli_override`)

Summary: `TOTAL: 8, PASS: 8, FAIL: 0, EXIT: 0`

## Style Vocab Metrics (current implementation checks)

- in-vocab sample: `style_vocab_hit_rate=1.0`, `style_oov_ratio=0.0`
- OOV sample (forced): blocked and replaced (`style_replacements=5`)
- LLM call count unchanged: `llm_calls=1`
