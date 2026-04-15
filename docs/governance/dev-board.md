# Development Board (Single Source)

> Single source board.
> Auto-updated by `tools/scripts/next_gate.ps1`.

## Current State (auto)

- Task: task-34
- Completed Gates: 9/9
- Next Gate: DONE

## Gate Checklist (auto-enforced)

- [x] G0 Handoff
- [x] G1 Plan + PRD mapping
- [x] G2 Red evidence
- [x] G3 Green evidence
- [x] G4 Refactor verify
- [x] G5 Docs consistency
- [x] G6 Hooks gate (commit-msg / pre-push)
- [x] G7 CI + audit gate
- [x] G8 Stage quality review

## Hook / CI Link (auto)

- [x] commit-msg passed
- [x] pre-push passed
- [x] CI workflow configured


## PRD Full TODO (from JSON)

- Source: docs/governance/prd-tdd-checklist.json
- Tasks Done: 52/52 ✅ COMPLETE

- [x] PHASE-01 Foundations & Guardrails (4/4)
  - [x] P01.01 Finalize one-law and non-negotiable red lines in runtime checks
  - [x] P01.02 Complete hook chain installation and enforce no-bypass policy
  - [x] P01.03 Pin dependency baseline from PRD and verify Windows-native install
  - [x] P01.04 Create reproducible bootstrap command and startup health check

- [x] PHASE-02 System Architecture Skeleton (3/3)
  - [x] P02.01 Create module skeleton for 6 business tools + 2 self-check tools
  - [x] P02.02 Define typed contracts between agent core and tools
  - [x] P02.03 Wire project filesystem conventions (git/json/sqlite/audio)

- [x] PHASE-03 Agent Contract (ReAct) (4/4)
  - [x] P03.01 Implement plan-first behavior for long-running actions
  - [x] P03.02 Implement interrupt/resume and state checkpointing
  - [x] P03.03 Implement user-facing natural-language result translation
  - [x] P03.04 Implement context auto-retrieval from project memory

- [x] PHASE-04 Tool 1 Acoustic Analyst (4/4)
  - [x] P04.01 Implement source preprocessing and optional Demucs path
  - [x] P04.02 Implement Parselmouth feature extraction
  - [x] P04.03 Implement librosa MFCC and CLAP embedding extraction
  - [x] P04.04 Output validated voice_profile.json schema

- [x] PHASE-05 Tool 2 Style Deconstructor (4/4)
  - [x] P05.01 Implement reference audio decomposition pipeline
  - [x] P05.02 Implement BPM/key/structure extraction
  - [x] P05.03 Implement instrumentation and energy curve extraction
  - [x] P05.04 Output validated reference_dna.json schema

- [x] PHASE-06 Tool 3 Friction Calculator (4/4)
  - [x] P06.01 Implement hard-constraint compatibility scoring
  - [x] P06.02 Implement timbre fit scoring via embedding similarity
  - [x] P06.03 Implement verdict and adjustment generation
  - [x] P06.04 Output validated friction_report.json schema

- [x] PHASE-07 Tool 4 Lyric Architect (6/6)
  - [x] P07.01 Implement structure-grid planner from intent + reference
  - [x] P07.02 Implement draft lyric generation with few-shot corpus grounding
  - [x] P07.03 Implement vowel openness interceptor at peak notes
  - [x] P07.04 Implement tone collision interceptor
  - [x] P07.05 Implement anti-cliche density interceptor
  - [x] P07.06 Output validated lyrics.json schema

- [x] PHASE-08 Tool 5 Prompt Compiler (3/3)
  - [x] P08.01 Implement Suno style/lyrics/exclude field compiler
  - [x] P08.02 Implement breath-tag and difficult-syllable timing adaptation
  - [x] P08.03 Implement output package files and compile_log.json

- [x] PHASE-09 Tool 6 Post Processor (4/4)
  - [x] P09.01 Implement stem extraction and alignment flow
  - [x] P09.02 Implement dynamic de-essing and vocal enhancement chain
  - [x] P09.03 Implement bus mixdown and Matchering mastering integration
  - [x] P09.04 Output mastering logs and final artifacts

- [x] PHASE-10 Self-Healing Protocol (4/4)
  - [x] P10.01 Implement known-error dictionary + auto-fix layer
  - [x] P10.02 Implement shell_probe constrained execution
  - [x] P10.03 Implement py_eval constrained execution
  - [x] P10.04 Implement retry and fallback policy with max-3 attempts

- [x] PHASE-11 Terminal UX and Operational Flow (4/4)
  - [x] P11.01 Implement conversation-first CLI commands and routing
  - [x] P11.02 Implement terminal playback and artifact preview
  - [x] P11.03 Implement downloads watcher and auto-import flow
  - [x] P11.04 Implement project memory and cleanup suggestions

- [x] PHASE-12 Dataflow Integration (3/3)
  - [x] P12.01 Implement end-to-end dataflow orchestration from intent to artifacts
  - [x] P12.02 Implement deterministic intermediate artifacts and trace IDs
  - [x] P12.03 Implement integration smoke tests for full pipeline

- [x] PHASE-13 Non-Goals and Scope Guard (2/2)
  - [x] P13.01 Add automated guardrails for explicit non-goals from PRD
  - [x] P13.02 Add dependency and feature drift checks

- [x] PHASE-14 Acceptance and Release Readiness (3/3)
  - [x] P14.01 Map each acceptance item to runnable verification command
  - [x] P14.02 Run full acceptance suite and capture evidence pack
  - [x] P14.03 Finalize release checklist and handoff summary

## Current State (auto)

- Task: task-52
- Completed Gates: 9/9
- Next Gate: DONE ✅

## Command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/next_gate.ps1" -TaskId "01"
```

## Latest Engineering Log (manual)

- Date: 2026-04-13
- Scope: Runtime hardening + minimal subprocess framework (Python 3.13)
- Changes:
  - Added isolated Demucs wrapper: `src/producer_tools/business/demucs_subprocess_runner.py`
  - Added child process script: `tools/scripts/run_demucs.py`
  - Switched `post_processor._extract_stems` to unified subprocess protocol
  - Added prompt semantic gate + watcher idempotency/queue state machine
  - Added/updated tests:
    - `tests/test_demucs_subprocess_runner.py`
    - `tests/test_download_watcher_integration.py`
    - `tests/test_prompt_compiler.py`
    - `tests/test_post_processor.py`
- Verification:
  - `python -m pytest -q` => 184 passed
  - LSP error diagnostics clean for modified source files
- Notes:
  - Current Demucs path is controlled fallback on this host due torchaudio runtime issue; main flow remains stable and non-crashing.

- Date: 2026-04-14
- Scope: Lyric architect hard-constraint coupling + LLM-only test alignment
- Changes:
  - Strengthened lyric prompt hard constraints in `src/producer_tools/business/lyric_architect.py`:
    - Added explicit three-layer bans (lexical / sentence-pattern / semantic)
    - Added explicit reference-song hard constraints (sentence length distribution, pause rhythm, chorus hook)
    - Added section-aware chorus hook enforcement flag (`Chorus` / `Final Chorus`)
  - Kept offline mode explicitly disabled in lyric run path (`offline_lyrics_disabled`)
  - Updated `tests/test_lyric_architect.py`:
    - Added stable adapter for deterministic LLM-path tests
    - Added explicit offline-disabled test
    - Added prompt hard-constraint injection assertion test
  - Updated `tests/test_orchestrator.py`:
    - Added deterministic adapter for prompt-chain/file-output cases under LLM-only pipeline
- Verification:
  - `py -3.13 -m pytest tests/test_lyric_architect.py` => 32 passed
  - `py -3.13 -m pytest tests/test_orchestrator.py` => 10 passed
  - `lsp_diagnostics` (error) for `src/producer_tools/business/lyric_architect.py` => clean
- Notes:
  - Local default `pytest` (Python 3.9) still fails on `TypeAlias` import from contracts; project verification for this batch was executed under Python 3.13 as required.

- Date: 2026-04-14
- Scope: Template-locked lyric pipeline + real corpus wiring + mock-path removal
- Changes:
  - Replaced lyric few-shot primary path with template-locked guidance in `src/producer_tools/business/lyric_architect.py`:
    - removed `FEW_SHOT_CORPUS` static examples from generation flow
    - added real corpus loaders (`.txt/.json/.jsonl`) via `corpus_sources` / `corpus_registry_path`
    - added template binding (`structure_template` / `structure_template_path`) and prompt-level non-overridable skeleton constraints
    - added `require_real_corpus` gate (`corpus_not_configured` on missing corpus data)
  - Updated orchestration wiring in `src/producer_tools/orchestrator/orchestrator.py`:
    - pass template/corpus inputs through to `lyric_architect`
    - removed deprecated `allow_offline_lyrics` payload read
  - Removed placeholder stem fallback in `src/producer_tools/business/post_processor.py`:
    - `_extract_stems` now fails fast with `demucs_runtime_unavailable` instead of synthetic stems
  - Tightened style deconstruction runtime behavior in `src/producer_tools/business/style_deconstructor.py`:
    - when `use_demucs=true` and runtime unavailable, fail fast with `demucs_unavailable`
  - Added shared real-pipeline assets:
    - `projects/_shared/templates/modern_lostlove_v1.json`
    - `projects/_shared/corpus_registry.json`
  - Updated PRD wording in `AI-music-producer PRD_v1.1.md` to replace few-shot main path with template/corpus-registry main path.
  - Updated tests:
    - `tests/test_post_processor.py`
    - `tests/test_orchestrator.py`
    - `tests/test_style_deconstructor_pipeline.py`
- Verification:
  - `py -3.13 -m pytest tests/test_lyric_architect.py` => 32 passed
  - `py -3.13 -m pytest tests/test_orchestrator.py` => 10 passed
  - `py -3.13 -m pytest tests/test_post_processor.py` => 16 passed
  - `py -3.13 -m pytest tests/test_style_deconstructor_pipeline.py tests/test_style_deconstructor_bpm.py tests/test_style_deconstructor_instrumentation.py tests/test_reference_dna_output.py tests/test_reference_dna_schema.py` => 21 passed
  - `lsp_diagnostics` error checks clean for all modified source/test files
- Notes:
  - Real simulation run against `F:\Onedrive\桌面\Dancing with my phone - HYBS.flac` reached lyric stage and failed on upstream LLM auth (`401 Invalid Authentication`), confirming data pipeline wiring is real and no mock fallback was used.

- Date: 2026-04-14
- Scope: PM-mode full simulated-user rerun with local template/corpus pipeline
- Changes:
  - Added explicit OpenAI-compatible runtime config pass-through in lyric/orchestrator:
    - `llm_api_key`, `llm_base_url`, `llm_model`
  - Fixed prompt semantic gate deadlock in `prompt_compiler`:
    - always emits `[Instrument: ...]` header (fallback default when emphasis instruments absent)
  - Sanitized `.env.example` by removing embedded real API key placeholders
  - Updated `docs/api-setup.md` with local template/corpus operation instructions:
    - `structure_template_path`, `corpus_registry_path`, `require_real_corpus=true`
    - documented that CALEH is not used in this repo runtime path
  - Ran PM-mode end-to-end simulation output:
    - `.tmp/pm_sim_20260414/outputs_v2/`
    - produced `lyrics.json`, `suno_v1.txt`, `suno_v1_style.txt`, `suno_v1_exclude.txt`, `minimax_v1.txt`, `compile_log.json`
- Verification:
  - `py -3.13 -m pytest tests/test_lyric_architect.py` => 32 passed
  - `py -3.13 -m pytest tests/test_orchestrator.py` => 10 passed
  - `py -3.13 -m pytest tests/test_prompt_compiler.py` => 20 passed
  - `py -3.13 -m pytest tests/test_post_processor.py` => 16 passed
  - `py -3.13 -m pytest tests/test_style_deconstructor_pipeline.py tests/test_style_deconstructor_bpm.py tests/test_style_deconstructor_instrumentation.py tests/test_reference_dna_output.py tests/test_reference_dna_schema.py` => 21 passed
  - `lsp_diagnostics` errors clean for modified Python files

- Date: 2026-04-14
- Scope: One-law Step-1 local asset builder (zero-complexity tables)
- Changes:
  - Added one consolidated script: `tools/scripts/build_local_assets.py`
    - builds `visual_montage_nouns.json` from THUOCL selected files
    - builds `cliche_blacklist.json` from funNLP selected files
    - builds `shisanzhe_map.json` (13-rhyme mapping + open finals)
    - builds `chinese_pop_grids.json` via regex dehydration from local Chinese_Lyrics
  - Added tests first (TDD): `tests/test_build_local_assets.py`
- Verification:
  - `py -3.13 -m pytest tests/test_build_local_assets.py` => 2 passed
  - `lsp_diagnostics` errors clean for both new files

- Date: 2026-04-14
- Scope: Remaining JSON assets completed under one-law TDD
- Changes:
  - Extended `tools/scripts/build_local_assets.py` to additionally generate:
    - `modern_literary_lexicon.json`
    - `emotion_acoustic_router.json`
  - Maintained single-script execution path (no duplicate script/directory)
  - Updated `tests/test_build_local_assets.py` first to require new assets, then implemented minimal code until pass
- Verification:
  - pre-implementation test state: 1 failed (missing `modern_literary_lexicon.json`)
  - `py -3.13 -m pytest tests/test_build_local_assets.py` => 2 passed
  - `lsp_diagnostics` on `tools/scripts/build_local_assets.py` => clean
