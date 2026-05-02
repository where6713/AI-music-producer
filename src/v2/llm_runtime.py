from __future__ import annotations

import hashlib
import json
import os
import time
import time
from urllib import request


def call(prompt: str, temperature: float = 0.7) -> tuple[str, dict[str, object]]:
    key = os.getenv("OPENAI_API_KEY", "")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set for real LLM inference")
    t0 = time.time()
    payload = {
        "model": os.getenv("V2_MODEL", "gpt-3.5-turbo"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
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
    trace = {
        "provider": "openai",
        "temperature": temperature,
        "model": payload["model"],
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:12],
        "response_hash": hashlib.sha256(content.encode()).hexdigest()[:12],
        "tokens_in": int(usage.get("prompt_tokens", 0) or 0),
        "tokens_out": int(usage.get("completion_tokens", 0) or 0),
        "latency_ms": latency_ms,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return content, trace
