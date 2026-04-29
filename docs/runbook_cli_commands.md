# CLI Runbook (Current Canonical Commands)

## Purpose

- Provide a single, up-to-date command reference for agents and reviewers.
- Prevent drift between historical examples and current executable CLI entrypoints.

## Generation

- Base command:
  - `python -m apps.cli.main produce "<raw_intent>" --genre "<genre>" --mood "<mood>" --profile <profile_id> --out-dir "out/task011_runs/<run_id>" --verbose`

## PM Audit

- Run-id scoped audit (required for acceptance evidence):
  - `python -m apps.cli.main pm-audit --run-id <run_id>`

- Notes:
  - Avoid using `--last` for final acceptance claims.
  - Acceptance requires explicit run-id evidence.

## Gate Checks

- All gates:
  - `python -m apps.cli.main gate-check --all`

- G1 scope check:
  - `python -m apps.cli.main scope-check g1`

## Evidence Pack (Minimum)

- `out/task011_runs/<run_id>/trace.json`
- `out/task011_runs/<run_id>/lyric_payload.json`
- `out/task011_runs/<run_id>/audit.md`
- `out/task011_runs/<run_id>/lyrics.txt` (if run_status is pass)
