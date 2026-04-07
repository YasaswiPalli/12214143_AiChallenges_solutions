"""
segmenter.py
============
Intelligent text segmentation using NLTK sentence tokenization.
Merges short fragments, splits on conjunctions when scene count is low,
and caps at MAX_SCENES to keep image generation costs reasonable.
"""

import re
import logging
from typing import List

import nltk

logger = logging.getLogger(__name__)

MIN_WORDS = 6      # Merge segments shorter than this
MAX_SCENES = 8     # Hard cap to avoid runaway API calls


def _ensure_nltk() -> None:
    """Download NLTK data if not already present."""
    for pkg in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{pkg}")
        except LookupError:
            nltk.download(pkg, quiet=True)


def _merge_short_segments(sentences: List[str], min_words: int) -> List[str]:
    """
    Merge any segment with fewer than `min_words` words into the
    following segment (or the previous one if it is the last).
    """
    merged: List[str] = []
    buffer = ""

    for sentence in sentences:
        if not sentence.strip():
            continue
        if buffer:
            if len(buffer.split()) < min_words:
                buffer = buffer + " " + sentence
            else:
                merged.append(buffer.strip())
                buffer = sentence
        else:
            buffer = sentence

    if buffer:
        merged.append(buffer.strip())

    return merged


def _expand_short_list(segments: List[str]) -> List[str]:
    """
    If we have fewer than 3 scenes, try splitting on common conjunctions
    to expand the list for a richer storyboard experience.
    """
    if len(segments) >= 3:
        return segments

    expanded: List[str] = []
    split_pattern = re.compile(
        r"(?<=[a-zA-Z0-9]),?\s+(?=and |but |however |yet |so |because |when |while |after |before |as )",
        re.IGNORECASE,
    )
    for seg in segments:
        parts = split_pattern.split(seg)
        expanded.extend(p.strip() for p in parts if p.strip())

    return expanded if len(expanded) >= 3 else segments


def segment_text(text: str) -> List[str]:
    """
    Segment a narrative text block into a list of scene strings.

    Steps:
      1. NLTK sentence tokenisation
      2. Merge fragments shorter than MIN_WORDS
      3. Expand lists that are shorter than 3 scenes
      4. Cap at MAX_SCENES
    """
    _ensure_nltk()
    text = text.strip()
    if not text:
        return ["(empty input)"]

    try:
        raw_sentences: List[str] = nltk.sent_tokenize(text)
    except Exception as exc:
        logger.warning(f"NLTK tokenisation failed, falling back to split: {exc}")
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    # Normalise whitespace per sentence
    raw_sentences = [re.sub(r"\s+", " ", s).strip() for s in raw_sentences if s.strip()]

    if not raw_sentences:
        return [text]

    merged = _merge_short_segments(raw_sentences, MIN_WORDS)
    expanded = _expand_short_list(merged)

    # Cap
    scenes = expanded[:MAX_SCENES]

    logger.info(f"Segmented text into {len(scenes)} scene(s).")
    return scenes
