# Acceptance Checklist - Runnable Verification Commands

> Source: PRD v1.1 Section 13

This document maps each acceptance criterion to runnable verification commands.

## Prerequisites

```powershell
# Verify installation
python -m pytest tests/ -q  # Should pass all tests

# Verify tools are available
python -c "from producer_tools.business import acoustic_analyst, style_deconstructor, friction_calculator, lyric_architect, prompt_compiler, post_processor"
python -c "from producer_tools.self_check import shell_probe, py_eval"
python -c "from producer_tools.terminal import audio_player, cli_router, download_watcher, project_memory"
python -c "from producer_tools.orchestrator import orchestrator"
```

## Acceptance Criteria Verification

### 1. Cold Start
**Criterion**: First run downloads dependencies to `~/.music-producer/`

**Verification**:
```powershell
# Clean install simulation
Remove-Item -Recurse -Force ~/.music-producer -ErrorAction SilentlyContinue
python -c "from producer_tools.business import acoustic_analyst; print('Import OK')"
```

### 2. Voice Profile Extraction
**Criterion**: Upload 30s voice -> 60s to get `voice_profile.json` + natural language summary

**Verification**:
```powershell
# Unit test verification
python -m pytest tests/test_acoustic_analyst.py -v -k "test_run"
```

### 3. Reference Analysis
**Criterion**: 3min mp3 -> 120s for stem separation + DNA extraction

**Verification**:
```powershell
python -m pytest tests/test_style_deconstructor.py -v -k "test_run"
```

### 4. Friction Calculation
**Criterion**: One command to get readable conflict list + adjustment suggestions

**Verification**:
```powershell
python -m pytest tests/test_friction_calculator.py -v -k "test_run"
```

### 5. Lyric Generation
**Criterion**: Intent -> 3min to get lyrics through physics/phonetics/semantic filters

**Verification**:
```powershell
python -m pytest tests/test_lyric_architect.py -v -k "test_run"
```

### 6. Prompt Compilation
**Criterion**: One command to get Suno Prompt package (Style/Lyrics/Exclude) -> clipboard

**Verification**:
```powershell
python -m pytest tests/test_prompt_compiler.py -v -k "test_run"
```

### 7. Auto-Import
**Criterion**: Suno download -> 10s auto-import + notification

**Verification**:
```powershell
python -m pytest tests/test_terminal_ux.py::TestDownloadWatcherContract -v
```

### 8. Post-Processing
**Criterion**: One command for de-AI + mixing + mastering -> 24bit WAV

**Verification**:
```powershell
python -m pytest tests/test_post_processor.py -v -k "test_run"
```

### 9. Terminal Playback
**Criterion**: `play master` in terminal, no external player

**Verification**:
```powershell
python -m pytest tests/test_terminal_ux.py::TestAudioPlayerContract -v
```

### 10. Branch Experiments
**Criterion**: "Try rock version" -> Agent creates branch, re-runs friction + prompt, can switch back

**Verification**:
```powershell
python -m pytest tests/test_terminal_ux.py::TestCLIRouterContract -v
```

### 11. Self-Healing
**Criterion**: Simulate sampling rate conflict or dependency missing -> Agent diagnoses + fixes autonomously

**Verification**:
```powershell
python -m pytest tests/test_self_check.py -v
```

### 12. Cleanup
**Criterion**: After 10 discarded takes, Agent actively reminds and cleans up

**Verification**:
```powershell
python -m pytest tests/test_terminal_ux.py::TestProjectMemoryContract -v
```

## Running Full Acceptance Suite

```powershell
# Run all tests
python -m pytest tests/ -q

# Expected: 171 passed

# Run scope guard checks
python -m pytest tests/test_scope_guard.py -v

# Expected: 10 passed
```

## Success Criteria

All 12 acceptance criteria = **DEPLOYABLE**
- Tests passing
- No Python errors in user-facing flows
- All tools functional
