import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
DIRS = ["_clean", "urban_introspective", "classical_restraint", "uplift_pop", "club_dance", "ambient_meditation", "indie_groove", "golden_dozen"]

def _row(item: dict, src: str) -> dict:
    content = str(item.get("content", "")).strip()
    first = next((ln.strip() for ln in content.splitlines() if ln.strip()), "")
    return {
        "id": str(item.get("source_id") or f"{src}:{item.get('title', 'untitled')}").strip(),
        "title": str(item.get("title", "")).strip(),
        "author": str(item.get("author", "")).strip(),
        "first_line": first,
        "summary_50chars": content[:50],
        "emotion_tags": [str(x) for x in item.get("emotion_tags", []) if str(x).strip()],
        "char_count": len(content.replace("\n", "")),
    }
def main() -> None:
    out: list[dict] = []
    by_dir: dict[str, int] = {d: 0 for d in DIRS}
    for d in DIRS:
        p = CORPUS / d
        if not p.exists():
            continue
        for f in sorted(p.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            for it in (data if isinstance(data, list) else []):
                if isinstance(it, dict) and str(it.get("content", "")).strip():
                    out.append(_row(it, f"corpus/{d}/{f.name}"))
                    by_dir[d] += 1
        for f in sorted(p.glob("*.txt")):
            lines = f.read_text(encoding="utf-8").splitlines()
            body = [ln for ln in lines if not ln.strip().startswith("#")]
            content = "\n".join(ln for ln in body if ln.strip())
            if not content.strip():
                continue
            out.append(_row({"source_id": f"corpus/{d}/{f.name}", "title": f.stem, "content": content}, ""))
            by_dir[d] += 1
    (CORPUS / "_index.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total={len(out)}")
    print(f"by_dir={json.dumps(by_dir, ensure_ascii=False)}")
if __name__ == "__main__":
    main()
