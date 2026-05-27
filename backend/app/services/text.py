"""Text processing: normalise, segment lyrics, deduplicate choruses."""

import hashlib
import re
import unicodedata
import uuid


def normalise_text(text: str) -> str:
    """Normalise text: unicode, whitespace, preserve punctuation."""
    # Unicode normalisation (NFC for composed characters)
    text = unicodedata.normalize("NFC", text)
    # Collapse multiple spaces/tabs but preserve newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Remove trailing spaces per line
    lines = [line.strip() for line in text.splitlines()]
    # Collapse more than 2 consecutive blank lines
    result = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()


def segment_lyrics(
    lyrics: str,
    track_id: str,
    min_lines: int = 1,
    max_lines: int = 3,
    stride: int = 1,
) -> list[dict]:
    """
    Segment lyrics into overlapping windows of 1–3 lines.
    Returns list of segment dicts with text, line_offset, context.
    """
    lines = [l for l in lyrics.splitlines() if l.strip()]
    if not lines:
        return []

    segments = []
    for start in range(0, len(lines), stride):
        for window in range(min_lines, max_lines + 1):
            end = start + window
            if end > len(lines):
                break
            chunk = lines[start:end]
            text = " ".join(chunk)
            if len(text) < 3:
                continue

            # Context: 1 line before and 1 after
            context_start = max(0, start - 1)
            context_end = min(len(lines), end + 1)
            context = "\n".join(lines[context_start:context_end])

            segment_id = str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{track_id}:{start}:{end}"
            ))

            segments.append({
                "segment_id": segment_id,
                "track_id": track_id,
                "text": text,
                "line_offset": start,
                "context": context,
            })

    return segments


def deduplicate_segments(segments: list[dict]) -> list[dict]:
    """
    Remove exact duplicate text (repeated choruses), keeping the first occurrence.
    Attaches a `is_duplicate` flag to duplicates so they can be filtered or kept.
    """
    seen: set[str] = set()
    result = []
    for seg in segments:
        text_hash = hashlib.md5(seg["text"].lower().encode()).hexdigest()
        if text_hash not in seen:
            seen.add(text_hash)
            seg["is_duplicate"] = False
            result.append(seg)
        # Skip duplicate segments entirely for now (can keep with flag if needed)
    return result


def sanitise_es_query(query: str) -> str:
    """Escape characters that have special meaning in Elasticsearch query strings."""
    special = r'+-=&|!(){}[]^"~*?:\\/'
    result = []
    for char in query:
        if char in special:
            result.append(f"\\{char}")
        else:
            result.append(char)
    return "".join(result)
