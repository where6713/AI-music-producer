# R00 Root Cause Analysis (TASK-013 continuation, P0)

## Scope and method
- Data source: `out/runs/task013_e2e*/trace.json` (16 runs)
- Check dimensions:
  - Which call stage first emits empty structure (`lyrics_by_section=[]`)
  - Whether `raw_model_output` is empty/truncated or parser-normalization collapsed
  - Whether Call#3 prompt role drifted from review to rewrite

## Q1. Empty structure origin and stage rates

Observed from trace stats:

- `call#2 (revise_trace)`: total 16, empty 7, rate **43.8%**
- `call#3 (call3_review_trace)`: total 6, empty 2, rate **33.3%**
- `call#4 (call4_final_trace)`: total 1, empty 1, rate **100%** (sample size 1)

Conclusion:
- Empty structure is primarily introduced at **Call#2**, then can propagate into Call#3/4.

## Step 1 required raw-shape classification (16-run sample set)

Classification target: all samples where `normalized_payload.lyrics_by_section == []`.

Result:
- Empty samples found: **10**
- Shape distribution:
  - `lyrics_by_section_variant_map`: **10/10**
  - top-level `{variant_a:...}`: **0/10**
  - top-level array `[{variant_id,...}]`: **0/10**
  - section-name alias drift (`Verse1/主歌/...`): **0/10**
  - markdown code-block wrapped JSON: **0/10**

Observed common raw shape (all 10):
- Top-level keys include `few_shot_examples_used/distillation/structure/lyrics_by_section/variants/chosen_variant_id`
- `lyrics_by_section` is a variant-keyed object (`a/b/c`), not a direct section-array
- Raw JSON itself is non-empty and parseable; collapse happens during normalization extraction

Example sample list (all classified as `lyrics_by_section_variant_map`):
- `task013_e2e_4` stage2
- `task013_e2e_b3` stage2
- `task013_e2e_b4` stage2
- `task013_e2e_c2` stage2
- `task013_e2e_c4` stage2
- `task013_e2e_c5` stage2
- `task013_e2e_2` stage3
- `task013_e2e_b1` stage3
- `task013_e2e_1` stage4
- `task013_e2e_5` stage2

## Q2. Raw output bad vs parser bad

Representative failing runs inspected: `task013_e2e_1`, `task013_e2e_2`, `task013_e2e_4`, `task013_e2e_c2`.

Facts from trace:
- `raw_model_output` is present in all failing calls (`raw_len` ~3.2k–4.7k)
- `shape_validation_report` often reports `ok=true` with `shape=object<variant_id,section_like>`
- But `normalized_payload.lyrics_by_section` becomes `[]`

Interpretation:
- This is **not** an empty response / transport truncation issue.
- This is a **normalization/parser collapse** case: raw has content, but extraction to normalized base sections fails for some variant-keyed structures.

Root-cause decision:
- Primary bug is in parser/normalization robustness around variant-keyed `lyrics_by_section` forms, not max_tokens or network.

## Q3. Is Call#3 prompt role drifted to rewrite?

Current code evidence (`src/main.py`):
- Call#3 uses `SECTION_REBIRTH_REVISE_PROMPT` with wording:
  - "段级重生 revise"
  - "允许换意象、允许重排句式"

This is rewrite behavior, not review-only behavior.

Conclusion:
- **Yes**, Call#3 role has drifted into rewrite scope, violating the intended "审校仅检查语病/凑韵，不改结构不改字数" boundary.

## P0 fix intent (before code changes)

Per stop-loss instruction, P0 only:

1. Harden revise output contract prompt (format constraints) to reduce parser-ambiguous layouts.
2. Add parser-side schema-validation retry once (internal repair pass, not counted in 4-call business budget).
3. Restore Call#3 prompt to strict review duty (no rewrite verbs, no structure change, no word-count change).

No quality-floor relaxation, no additional fallback layers in P0.
