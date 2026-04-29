# Issue 19 Task Evidence

## TASK-001 BUG-01 provider routing and key validation
- status: done
- evidence_id: EVD-001
- command: `python -m pytest -q tests/test_v2_claude_client.py`
- result: pass

## TASK-002 BUG-02 variants normalization and chosen fallback
- status: done
- evidence_id: EVD-002
- command: `python -m pytest -q tests/test_v2_claude_client.py`
- result: pass

## TASK-003 BUG-03 lint/retriever gate alignment
- status: done
- evidence_id: EVD-003
- command: `python -m pytest -q tests/test_corpus_quality.py tests/test_v2_retriever.py`
- result: pass

## TASK-004 BUG-04 Chinese numeric detection
- status: done
- evidence_id: EVD-004
- command: `python -m pytest -q tests/test_corpus_quality.py`
- result: pass

## TASK-005 OPS-01 dry-run error observability
- status: done
- evidence_id: EVD-005
- command: `python -m pytest -q tests/test_v2_main_variants.py`
- result: pass

## TASK-006 PM audit numeric id false-positive fix
- status: done
- evidence_id: EVD-006
- command: `python -m pytest -q tests/test_v2_g7.py`
- result: pass

## TASK-014 end-to-end closure checks
- status: done
- evidence_id: EVD-014
- command: `python -m pytest -q`
- result: `182 passed`
- command: `python -m apps.cli.main produce "门缝漏进楼道里的回声" --profile urban_introspective --verbose --out-dir "out/task011_runs/issue19_run"`
- result: generated outputs and trace
- command: `python -m apps.cli.main pm-audit --run-id issue19_run`
- result: `TOTAL: 8, PASS: 8, FAIL: 0, EXIT: 0`
- command: corpus clean scan for mock/fake ids and Chinese-number placeholders
- result: no matches
