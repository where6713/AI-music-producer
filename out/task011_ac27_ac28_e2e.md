# TASK-011 AC_27 / AC_28 E2E Evidence

## Commands
- `python -c "from src.main import produce\nproduce(raw_intent='古筝冥想风和水慢慢流',genre='ambient',mood='平静',vocal='any',profile='',lang='zh-CN',out_dir='G:\\\\AI-music-producer\\\\out\\\\task011_runs\\\\AM-01',verbose=True,dry_run=False)\n"`
- `python -c "from src.main import produce\nproduce(raw_intent='写一首古风留白山水意境',genre='古风',mood='意境',vocal='any',profile='',lang='zh-CN',out_dir='G:\\\\AI-music-producer\\\\out\\\\task011_runs\\\\CR-01',verbose=True,dry_run=False)\n"`
- `python -c "from src.main import produce\nproduce(raw_intent='青春热恋要明亮上口',genre='华语流行',mood='愉悦',vocal='any',profile='',lang='zh-CN',out_dir='G:\\\\AI-music-producer\\\\out\\\\task011_runs\\\\UP-01',verbose=True,dry_run=False)\n"`
- `python -c "from src.main import produce\nproduce(raw_intent='夜店舞池一起跳起来',genre='EDM',mood='热烈',vocal='any',profile='',lang='zh-CN',out_dir='G:\\\\AI-music-producer\\\\out\\\\task011_runs\\\\CD-01',verbose=True,dry_run=False)\n"`

## Output Paths
- AM-01: `out/task011_runs/AM-01` | `out/task011_runs/AM-01/trace.json`
- CR-01: `out/task011_runs/CR-01` | `out/task011_runs/CR-01/trace.json`
- UP-01: `out/task011_runs/UP-01` | `out/task011_runs/UP-01/trace.json`
- CD-01: `out/task011_runs/CD-01` | `out/task011_runs/CD-01/trace.json`

## Lint Fields
- AM-01: active=ambient_meditation, failed=[], skipped=['R15'], r16_sources=[]
- CR-01: active=classical_restraint, failed=[], skipped=['R15'], r16_sources=[]
- UP-01: active=uplift_pop, failed=[], skipped=[], r16_sources=[]
- CD-01: active=club_dance, failed=['R05'], skipped=['R15'], r16_sources=[]
