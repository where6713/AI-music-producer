from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas import LyricPayload, UserInput


def _load_skill_text(repo_root: Path) -> str:
    skill_path = repo_root / ".claude" / "skills" / "lyric-craftsman" / "SKILL.md"
    return skill_path.read_text(encoding="utf-8")


def _extract_json_block(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model output does not contain JSON object")
    return json.loads(text[start : end + 1])


def generate_lyric_payload(
    user_input: UserInput,
    *,
    repo_root: Path,
    model: str = "claude-opus-4-1-20250805",
) -> tuple[LyricPayload, dict[str, Any]]:
    from anthropic import Anthropic

    api_key = (repo_root / ".env").read_text(encoding="utf-8", errors="ignore")
    key = ""
    for line in api_key.splitlines():
        s = line.strip()
        if s.startswith("ANTHROPIC_API_KEY="):
            key = s.split("=", 1)[1].strip().strip('"').strip("'")
            break
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing in .env")

    client = Anthropic(api_key=key)
    skill_text = _load_skill_text(repo_root)

    prompt = {
        "task": "Generate lyric_payload JSON only.",
        "input": user_input.model_dump(),
    }

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0.4,
        system=skill_text,
        messages=[
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False),
            }
        ],
    )

    text_blocks = [
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ]
    raw_text = "\n".join(text_blocks)
    payload_dict = _extract_json_block(raw_text)
    payload = LyricPayload.model_validate(payload_dict)

    trace = {
        "model": model,
        "usage": {
            "input_tokens": getattr(message.usage, "input_tokens", 0),
            "output_tokens": getattr(message.usage, "output_tokens", 0),
        },
        "llm_calls": 1,
    }
    return payload, trace
