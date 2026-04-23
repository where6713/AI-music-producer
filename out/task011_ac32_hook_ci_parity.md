# TASK-011 AC_32 Hook / CI Parity

| check | parity |
| --- | --- |
| pytest -q | True |
| apps.cli.main pm-audit | True |
| out/lyrics.txt | True |
| out/style.txt | True |
| out/exclude.txt | True |

命令证据：
- `python -m apps.cli.main hook-check g5`
- `python -m apps.cli.main ci-gate-check g6`
