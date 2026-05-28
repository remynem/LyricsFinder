import hashlib
import re
import unicodedata
import uuid


def normalise_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    result, blank_count = [], 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()


def segment_lyrics(lyrics: str, track_id: str, min_lines: int = 1, max_lines: int = 3, stride: int = 1) -> list[dict]:
    lines = [l for l in lyrics.splitlines() if l.strip()]
    if not lines:
        return []
    segments = []
    for start in range(0, len(lines), stride):
        for window in range(min_lines, max_lines + 1):
            end = start + window
            if end > len(lines):
                break
            text = " ".join(lines[start:end])
            if len(text) < 3:
                continue
            context = "\n".join(lines[max(0, start - 1):min(len(lines), end + 1)])
            segment_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{track_id}:{start}:{end}"))
            segments.append({"segment_id": segment_id, "track_id": track_id,
                             "text": text, "line_offset": start, "context": context})
    return segments


def deduplicate_segments(segments: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for seg in segments:
        h = hashlib.md5(seg["text"].lower().encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(seg)
    return result


def sanitise_es_query(query: str) -> str:
    special = r'+-=&|!(){}[]^"~*?:\\/'
    return "".join(f"\\{c}" if c in special else c for c in query)
