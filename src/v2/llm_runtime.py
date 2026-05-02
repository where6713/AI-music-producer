from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from urllib import request


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if v})
    return env


def call(prompt: str, temperature: float = 0.7) -> tuple[str, dict[str, object]]:
    env = _load_env()
    key = env.get("OPENAI_API_KEY") or env.get("ANTHROPIC_API_KEY") or ""
    base = env.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = env.get("OPENAI_MODEL") or env.get("ANTHROPIC_MODEL") or "gpt-3.5-turbo"
    if not key:
        raise RuntimeError("No LLM credential found: set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")
    t0 = time.time()
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
    req = request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode()
    decoded = json.loads(body)
    content = decoded.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = decoded.get("usage", {})
    latency_ms = int((time.time() - t0) * 1000)
    meta: dict[str, object] = {
        "provider": "openai-compatible" if "OPENAI_API_KEY" in env else "anthropic",
        "model": model,
        "temperature": temperature,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:12],
        "response_hash": hashlib.sha256(content.encode()).hexdigest()[:12],
        "tokens_in": int(usage.get("prompt_tokens", 0) or 0),
        "tokens_out": int(usage.get("completion_tokens", 0) or 0),
        "latency_ms": latency_ms,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return content, meta
