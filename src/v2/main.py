from __future__ import annotations

from pathlib import Path

from .compose import compose
from .distill_emotion import distill_emotion
from .perceive_music import perceive_music
from .select_corpus import select_corpus
from .self_review import self_review


def run_v2(raw_intent: str, ref_audio: str = "", index_path: str = "corpus/_index.json") -> dict[str, object]:
    portrait = perceive_music(raw_intent, ref_audio=ref_audio)
    emotion = distill_emotion(raw_intent, portrait)
    pool = select_corpus(Path(index_path), portrait, limit=100)
    golden = [x for x in pool if "golden_dozen" in str(x.get("id", ""))][:12]
    draft = compose(portrait, emotion, golden_refs=golden, corpus_pool=pool)
    return self_review(draft)
