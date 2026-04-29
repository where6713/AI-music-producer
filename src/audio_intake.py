from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
from urllib import request


def _read_env_map(repo_root: Path) -> dict[str, str]:
    env_path = repo_root / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def _resolve_model_config(repo_root: Path) -> dict[str, str]:
    env_map = _read_env_map(repo_root)
    anthropic_key = env_map.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key and not anthropic_key.startswith("sk-kimi-"):
        return {
            "provider": "anthropic",
            "api_key": anthropic_key,
            "model": env_map.get("ANTHROPIC_MODEL", "").strip() or "claude-opus-4-1-20250805",
            "base_url": "",
        }
    openai_key = env_map.get("OPENAI_API_KEY", "").strip()
    openai_base = env_map.get("OPENAI_BASE_URL", "").strip()
    openai_model = env_map.get("OPENAI_MODEL", "").strip()
    if openai_key and openai_base and openai_model:
        return {
            "provider": "openai-compatible",
            "api_key": openai_key,
            "model": openai_model,
            "base_url": openai_base,
        }
    moonshot_key = env_map.get("MOONSHOT_API_KEY", "").strip()
    moonshot_base = env_map.get("MOONSHOT_BASE_URL", "").strip()
    moonshot_model = env_map.get("MOONSHOT_MODEL", "").strip()
    if moonshot_key and moonshot_base and moonshot_model:
        return {
            "provider": "openai-compatible",
            "api_key": moonshot_key,
            "model": moonshot_model,
            "base_url": moonshot_base,
        }
    return {}


def _parse_bpm_text(raw: str) -> int | None:
    text = str(raw or "").strip()
    match = re.search(r"\b(6[0-9]|7[0-9]|8[0-9]|9[0-9]|1[0-8][0-9]|190)\b", text)
    if not match:
        return None
    try:
        bpm = int(match.group(1))
    except ValueError:
        return None
    if 60 <= bpm <= 190:
        return bpm
    return None


def _infer_bpm_with_llm(repo_root: Path, filename: str) -> int | None:
    cfg = _resolve_model_config(repo_root)
    if not cfg:
        return None
    prompt = (
        f"请根据歌名和歌手 \"{filename}\"，推断其原曲的近似 BPM。"
        "请使用音乐常识区间做约束："
        "indie pop 常见 90-115、dance/edm 常见 120-140、ambient 常见 60-90。"
        "如果歌曲信息不足，优先按最可能曲风在对应区间内给出保守值。"
        "只输出一个 60-190 之间的纯数字 BPM，禁止输出任何解释。"
    )
    try:
        if cfg.get("provider") == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=cfg["api_key"])
            message = client.messages.create(
                model=cfg["model"],
                max_tokens=16,
                temperature=0,
                system="You output one BPM integer only.",
                messages=[{"role": "user", "content": prompt}],
            )
            text_blocks = [
                block.text for block in message.content if getattr(block, "type", "") == "text"
            ]
            return _parse_bpm_text("\n".join(text_blocks))

        endpoint = cfg["base_url"].rstrip("/") + "/chat/completions"
        payload = {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": "You output one BPM integer only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 16,
        }
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        decoded = json.loads(body)
        content = decoded.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _parse_bpm_text(content)
    except Exception:
        return None


def _infer_bpm_from_name(path: Path) -> int | None:
    name = path.stem
    match = re.search(r"(?:^|[^0-9])(6[0-9]|7[0-9]|8[0-9]|9[0-9]|1[0-8][0-9]|190)(?:[^0-9]|$)", name)
    if not match:
        return None
    try:
        bpm = int(match.group(1))
    except ValueError:
        return None
    if 60 <= bpm <= 190:
        return bpm
    return None


def _budget_from_bpm(bpm: int, fallback: dict[str, Any]) -> tuple[int, int]:
    if bpm <= 75:
        return 140, 200
    if bpm <= 95:
        return 170, 230
    if bpm <= 120:
        return 190, 260
    if bpm <= 140:
        return 180, 250
    bmin = int(fallback.get("syllable_budget_min", 180) or 180)
    bmax = int(fallback.get("syllable_budget_max", 240) or 240)
    return bmin, bmax


def _line_min_max_from_source(source_max: int, default_delta: int = 3) -> tuple[int, int]:
    upper = int(source_max)
    lower = max(1, upper - default_delta)
    return lower, upper


def resolve_prosody_from_ref_audio(ref_audio_path: str, fallback: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    out = dict(fallback or {})
    path = Path(str(ref_audio_path or "").strip())
    if not path:
        return out
    if not path.exists():
        out["audio_intake"] = {"ok": False, "reason": "path_not_found", "path": str(path)}
        return out

    bpm: int | None = None
    source = "none"

    try:
        from mutagen import File as MutagenFile  # type: ignore

        meta = MutagenFile(str(path), easy=True)
        if meta is not None:
            candidates: list[Any] = []
            tags = getattr(meta, "tags", None)
            if tags is not None and hasattr(tags, "get"):
                for key in ("bpm", "tbpm", "tempo"):
                    value = tags.get(key)
                    if isinstance(value, list) and value:
                        candidates.append(value[0])
                    elif value is not None:
                        candidates.append(value)
            for value in candidates:
                try:
                    maybe = int(float(str(value).strip()))
                except ValueError:
                    continue
                if 60 <= maybe <= 190:
                    bpm = maybe
                    source = "mutagen_tags"
                    break
    except Exception:
        pass

    if bpm is None:
        bpm = _infer_bpm_from_name(path)
        if bpm is not None:
            source = "filename"

    if bpm is None:
        bpm = _infer_bpm_with_llm(repo_root, path.stem)
        if bpm is not None:
            source = "llm_inference"

    if bpm is not None:
        bmin, bmax = _budget_from_bpm(bpm, fallback)
        verse_max = int(fallback.get("verse_line_max", 8) or 8)
        chorus_max = int(fallback.get("chorus_line_max", 8) or 8)
        bridge_max = int(fallback.get("bridge_line_max", 10) or 10)
        verse_min, verse_max = _line_min_max_from_source(verse_max)
        chorus_min, chorus_max = _line_min_max_from_source(chorus_max)
        bridge_min, bridge_max = _line_min_max_from_source(bridge_max)
        out["bpm"] = bpm
        out["bpm_source"] = source
        out["syllable_budget_min"] = bmin
        out["syllable_budget_max"] = bmax
        out["verse_line_min"] = verse_min
        out["verse_line_max"] = verse_max
        out["chorus_line_min"] = chorus_min
        out["chorus_line_max"] = chorus_max
        out["bridge_line_min"] = bridge_min
        out["bridge_line_max"] = bridge_max
        out["audio_intake"] = {"ok": True, "source": source, "path": str(path)}
        return out

    out["audio_intake"] = {"ok": False, "reason": "bpm_unavailable", "path": str(path)}
    return out
