from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    raw_intent: str
    language: Literal["zh-CN", "en-US"] = "zh-CN"
    genre_hint: str = ""
    mood_hint: str = ""
    vocal_gender_hint: Literal["male", "female", "any"] = "any"


class Distillation(BaseModel):
    emotional_register: str
    core_tension: str
    valence: Literal["positive", "negative", "mixed"]
    arousal: Literal["low", "medium", "high"]
    forbidden_literal_phrases: list[str] = Field(default_factory=list)


class Structure(BaseModel):
    section_order: list[str]
    hook_section: str = "[Chorus]"
    hook_line_index: int = 1


class LyricLine(BaseModel):
    primary: str
    backing: str = ""
    tail_pinyin: str = ""
    char_count: int = 0


class LyricSection(BaseModel):
    tag: str
    voice_tags_inline: list[str] = Field(default_factory=list)
    lines: list[LyricLine]


class StyleTags(BaseModel):
    genre: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)
    instruments: list[str] = Field(default_factory=list)
    vocals: list[str] = Field(default_factory=list)
    production: list[str] = Field(default_factory=list)


class LyricPayload(BaseModel):
    schema_version: str = "v2.0"
    generation_id: str = Field(default_factory=lambda: str(uuid4()))
    model_used: str = "claude-opus-4-7"
    skill_used: str = "lyric-craftsman@v1.0"
    distillation: Distillation
    structure: Structure
    lyrics_by_section: list[LyricSection]
    style_tags: StyleTags
    exclude_tags: list[str] = Field(default_factory=list)
