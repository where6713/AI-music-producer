"""Prompt Compiler tool for Suno/MiniMax prompt generation.

PRD 5.5: Compiles friction_report + genre_seed + lyrics.json
into Suno/MiniMax compatible prompt format with three fields:
1. Style field - genre/BPM/key/vocal style/instruments
2. Lyrics field - structured lyrics with mood/energy/instrument tags
3. Exclude field - negative prompt blacklist
"""

from __future__ import annotations

from ..contracts import ToolPayload, ToolResult

TOOL_NAME = "prompt_compiler"

# PRD 5.5: Default exclude blacklist
DEFAULT_EXCLUDE_BLACKLIST = [
    "metal",
    "screamo",
    "autotune heavy",
    "distorted vocal",
    "8-bit",
    "chiptune",
]

# PRD 5.5: Section mood descriptors by energy level
ENERGY_MOOD_MAP = {
    "low": "intimate, moody",
    "medium": "reflective",
    "high": "building",
    "peak": "explosive release",
}


def _extract_bpm(reference_dna: dict[str, object]) -> float:
    """Extract BPM from normalized or legacy style_deconstructor fields."""
    bpm = reference_dna.get("bpm")
    if isinstance(bpm, (int, float)) and bpm > 0:
        return float(bpm)

    tempo = reference_dna.get("tempo")
    if isinstance(tempo, (int, float)) and tempo > 0:
        return float(tempo)

    return 0.0


def _extract_emphasis_instruments(reference_dna: dict[str, object]) -> list[str]:
    """Extract emphasis instruments from both target and legacy schemas."""
    instrumentation = reference_dna.get("instrumentation", {})
    if not isinstance(instrumentation, dict):
        return []

    emphasis = instrumentation.get("emphasis", [])
    if isinstance(emphasis, list):
        out = [str(inst) for inst in emphasis if isinstance(inst, str) and inst]
        if out:
            return out

    # style_deconstructor legacy shape:
    # {"vocals": {"presence": True, ...}, "bass": {"presence": True, ...}}
    out: list[str] = []
    for stem, val in instrumentation.items():
        if isinstance(stem, str) and isinstance(val, dict):
            presence = val.get("presence")
            if presence is True:
                out.append(stem)
    return out


def _extract_energy_head(reference_dna: dict[str, object]) -> float:
    """Extract first energy value from list[float] or list[{energy:float}]."""
    energy_curve = reference_dna.get("energy_curve", [])
    if not isinstance(energy_curve, list) or not energy_curve:
        return 0.0

    head = energy_curve[0]
    if isinstance(head, (int, float)):
        return float(head)
    if isinstance(head, dict):
        energy = head.get("energy")
        if isinstance(energy, (int, float)):
            return float(energy)

    return 0.0


def compile_style_field(
    genre_seed: dict[str, object],
    reference_dna: dict[str, object],
    voice_profile: dict[str, object],
) -> dict[str, object]:
    """Compile Suno Style field from genre seed, reference DNA, and voice profile.

    PRD 5.5: Style field format:
    {genre_seed.descriptors}, {target_key}, {tempo_bpm} BPM,
    {vocal_style_tags}, {instrumentation_emphasis}

    Args:
        genre_seed: dict with descriptors (list of genre tags)
        reference_dna: dict with key, bpm, instrumentation
        voice_profile: dict with timbre.brightness for vocal style inference

    Returns:
        dict with ok, style (string)
    """
    try:
        parts: list[str] = []

        # 1. Genre descriptors
        descriptors = genre_seed.get("descriptors", [])
        if isinstance(descriptors, list):
            for d in descriptors:
                if isinstance(d, str) and d:
                    parts.append(d)

        # 2. Target key
        key = reference_dna.get("key", "")
        if isinstance(key, str) and key:
            parts.append(key)

        # 3. BPM
        bpm = _extract_bpm(reference_dna)
        if bpm > 0:
            parts.append(f"{int(bpm)} BPM")

        # 4. Vocal style from timbre brightness
        timbre = voice_profile.get("timbre", {})
        if isinstance(timbre, dict):
            brightness = timbre.get("brightness", 0.5)
            if isinstance(brightness, (int, float)):
                if brightness > 0.7:
                    parts.append("bright vocal")
                elif brightness > 0.4:
                    parts.append("warm vocal")
                else:
                    parts.append("deep vocal")

        # 5. Instrumentation emphasis
        for inst in _extract_emphasis_instruments(reference_dna):
            parts.append(inst)

        style = ", ".join(parts)

        return {
            "ok": True,
            "style": style,
            "source": {
                "genre": "genre_seed.descriptors",
                "key_bpm": "reference_dna",
                "vocal_style": "inferred_from_timbre",
                "instruments": "reference_dna.instrumentation.emphasis",
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "style": "",
        }


def compile_lyrics_field(
    lyrics: dict[str, object],
    reference_dna: dict[str, object],
) -> dict[str, object]:
    """Compile Suno Lyrics field with structure tags and mood descriptors.

    PRD 5.5: Lyrics field includes:
    [Mood: ...] [Energy: ...] [Instrument: ...]
    [Verse 1] [mood descriptor]
    lyrics text...

    Args:
        lyrics: dict with sections (list of section dicts with tag, lines)
        reference_dna: dict with energy_curve, instrumentation

    Returns:
        dict with ok, lyrics (string)
    """
    try:
        sections = lyrics.get("sections", [])
        if not isinstance(sections, list):
            sections = []

        if not sections:
            return {"ok": True, "lyrics": ""}

        lines: list[str] = []

        # Header: Mood/Energy/Instrument tags
        start_energy = _extract_energy_head(reference_dna)
        if start_energy > 0:
            if start_energy > 0.7:
                lines.append("[Mood: energetic]")
            elif start_energy > 0.4:
                lines.append("[Mood: reflective]")
            else:
                lines.append("[Mood: intimate]")

        emphasis = _extract_emphasis_instruments(reference_dna)
        if emphasis:
            top_3 = emphasis[:3]
            if top_3:
                lines.append(f"[Instrument: {', '.join(str(i) for i in top_3)}]")
        else:
            lines.append("[Instrument: vocal, soft drums, synth pad]")

        # Section content
        for section in sections:
            if not isinstance(section, dict):
                continue

            tag = section.get("tag", "Verse")
            section_lines = section.get("lines", [])

            if not isinstance(section_lines, list):
                section_lines = []

            # Add section header with mood
            mood = _get_mood_for_tag(tag)
            lines.append(f"\n[{tag}] [{mood}]")

            # Add lyrics text
            for line_data in section_lines:
                if isinstance(line_data, dict):
                    text = line_data.get("text", "")
                    if isinstance(text, str) and text:
                        # Check for tone collision warnings (difficult syllable timing)
                        warnings = line_data.get("warnings", [])
                        if isinstance(warnings, list) and "tone_collision" in warnings:
                            # Mark last character for timing adjustment
                            text = text[:-1] + "~" + text[-1] if len(text) > 1 else text
                        lines.append(text)
                elif isinstance(line_data, str):
                    lines.append(line_data)

        lyrics_text = "\n".join(lines)

        return {
            "ok": True,
            "lyrics": lyrics_text,
            "source": {
                "structure": "lyrics.sections",
                "mood": "derived_from_energy_curve",
                "timing_adjustments": "lyric_architect.warnings",
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "lyrics": "",
        }


def compile_exclude_field(
    reference_dna: dict[str, object],
) -> dict[str, object]:
    """Compile Suno Exclude Styles field from reference DNA.

    PRD 5.5: Exclude field includes:
    {instrumentation_deemphasis} + [metal, screamo, autotune heavy, ...]

    Args:
        reference_dna: dict with instrumentation.deemphasis

    Returns:
        dict with ok, exclude (string)
    """
    try:
        exclude_items: list[str] = []

        # Add user-specified deemphasis
        instrumentation = reference_dna.get("instrumentation", {})
        if isinstance(instrumentation, dict):
            deemphasis = instrumentation.get("deemphasis", [])
            if isinstance(deemphasis, list):
                for item in deemphasis:
                    if isinstance(item, str) and item:
                        exclude_items.append(item)

        # Add default blacklist
        for item in DEFAULT_EXCLUDE_BLACKLIST:
            if item not in exclude_items:
                exclude_items.append(item)

        exclude = ", ".join(exclude_items)

        return {
            "ok": True,
            "exclude": exclude,
            "source": {
                "deemphasis": "reference_dna.instrumentation.deemphasis",
                "default_blacklist": "PRD_5.5_spec",
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "exclude": "",
        }


def _get_mood_for_tag(tag: str) -> str:
    """Get mood descriptor for section tag.

    Args:
        tag: Section tag (e.g., "Verse 1", "Chorus", "Bridge")

    Returns:
        Mood descriptor string
    """
    tag_lower = tag.lower()

    if "chorus" in tag_lower:
        return "explosive release"
    elif "bridge" in tag_lower:
        return "tonal shift, distant reverb"
    elif "pre" in tag_lower:
        return "build-up"
    elif "outro" in tag_lower:
        return "fade"
    elif "intro" in tag_lower:
        return "atmospheric"
    else:
        return "intimate, moody"


def validate_prompt_semantics(
    style_text: str,
    lyrics_text: str,
    exclude_text: str,
) -> dict[str, object]:
    """Validate semantic completeness of Suno prompt slots."""
    violations: list[str] = []

    if "BPM" not in style_text:
        violations.append("style_missing_bpm")

    has_key_token = any(
        k in style_text for k in [" major", " minor", "C#", "D#", "F#", "G#", "A#"]
    )
    if not has_key_token:
        violations.append("style_missing_key")

    if "[Mood:" not in lyrics_text:
        violations.append("lyrics_missing_mood_tag")
    if "[Instrument:" not in lyrics_text:
        violations.append("lyrics_missing_instrument_tag")
    if "[Verse 1]" not in lyrics_text:
        violations.append("lyrics_missing_verse1")
    if "[Chorus" not in lyrics_text:
        violations.append("lyrics_missing_chorus")

    if not exclude_text.strip():
        violations.append("exclude_missing")

    return {
        "pass": len(violations) == 0,
        "violations": violations,
    }


def run(payload: ToolPayload) -> ToolResult:
    """Execute the prompt_compiler tool.

    PRD 5.5: Compiles genre_seed + reference_dna + lyrics
    into Suno-compatible prompt format with style, lyrics, exclude fields.

    Args:
        payload: dict with genre_seed, reference_dna, lyrics, optional voice_profile

    Returns:
        dict with ok, style, lyrics, exclude, compile_log
    """
    # Skeleton check
    if payload.get("_skeleton"):
        raise NotImplementedError("prompt_compiler tool skeleton")

    # Extract inputs
    genre_seed_raw = payload.get("genre_seed", {})
    genre_seed: dict[str, object] = (
        genre_seed_raw if isinstance(genre_seed_raw, dict) else {}
    )
    reference_dna_raw = payload.get("reference_dna", {})
    reference_dna: dict[str, object] = (
        reference_dna_raw if isinstance(reference_dna_raw, dict) else {}
    )
    lyrics_raw = payload.get("lyrics", {})
    lyrics: dict[str, object] = lyrics_raw if isinstance(lyrics_raw, dict) else {}
    voice_profile_raw = payload.get("voice_profile", {})
    voice_profile: dict[str, object] = (
        voice_profile_raw if isinstance(voice_profile_raw, dict) else {}
    )
    semantic_gate = bool(payload.get("semantic_gate", True))

    # Validate required inputs
    if not isinstance(reference_dna, dict) or not reference_dna:
        return {
            "ok": False,
            "error": "reference_dna_required",
            "style": "",
            "lyrics": "",
            "exclude": "",
            "compile_log": {},
        }

    # Compile three fields
    style_result = compile_style_field(genre_seed, reference_dna, voice_profile)
    lyrics_result = compile_lyrics_field(lyrics, reference_dna)
    exclude_result = compile_exclude_field(reference_dna)

    # Build compile log
    compile_log = {
        "style_source": style_result.get("source", {}),
        "lyrics_source": lyrics_result.get("source", {}),
        "exclude_source": exclude_result.get("source", {}),
        "timestamp": "auto-generated",
    }

    # Check for failures
    if not style_result.get("ok"):
        return {
            "ok": False,
            "error": style_result.get("error", "style_compilation_failed"),
            "style": "",
            "lyrics": lyrics_result.get("lyrics", ""),
            "exclude": exclude_result.get("exclude", ""),
            "compile_log": compile_log,
        }

    if not lyrics_result.get("ok"):
        return {
            "ok": False,
            "error": lyrics_result.get("error", "lyrics_compilation_failed"),
            "style": style_result.get("style", ""),
            "lyrics": "",
            "exclude": exclude_result.get("exclude", ""),
            "compile_log": compile_log,
        }

    if not exclude_result.get("ok"):
        return {
            "ok": False,
            "error": exclude_result.get("error", "exclude_compilation_failed"),
            "style": style_result.get("style", ""),
            "lyrics": lyrics_result.get("lyrics", ""),
            "exclude": "",
            "compile_log": compile_log,
        }

    style_text = str(style_result.get("style", ""))
    lyrics_text = str(lyrics_result.get("lyrics", ""))
    exclude_text = str(exclude_result.get("exclude", ""))

    semantic_result = validate_prompt_semantics(style_text, lyrics_text, exclude_text)
    compile_log["semantic_gate"] = semantic_result

    if semantic_gate and not semantic_result.get("pass", False):
        return {
            "ok": False,
            "error": "semantic_gate_failed",
            "style": style_text,
            "lyrics": lyrics_text,
            "exclude": exclude_text,
            "compile_log": compile_log,
            "semantic_gate": semantic_result,
        }

    return {
        "ok": True,
        "style": style_text,
        "lyrics": lyrics_text,
        "exclude": exclude_text,
        "compile_log": compile_log,
        "semantic_gate": semantic_result,
    }
