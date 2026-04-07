"""
ssml_builder.py
───────────────
Feature ③ — SSML Integration

Builds a Speech Synthesis Markup Language (SSML) document from plain text,
injecting:
  • <emphasis level="strong">   for ALL-CAPS words (shouted/stressed)
  • <emphasis level="moderate"> for intensifier words (very, extremely, …)
  • <break time="250ms"/>       after sentence-ending punctuation (. ; :)
  • <break time="100ms"/>       after exclamations (!)
  • <break time="75ms"/>        after commas

The output is wrapped in:
  <speak>
    <prosody rate="…" pitch="…" volume="…">
      ... transformed text ...
    </prosody>
  </speak>

edge-tts automatically detects SSML input and processes the tags correctly.
"""

from __future__ import annotations
import re
import html
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from emotion_detector import VoiceProfile

logger = logging.getLogger(__name__)

# Intensifiers that get <emphasis level="moderate">
_INTENSIFIER_SET = {
    "absolutely", "completely", "entirely", "extremely", "incredibly",
    "insanely", "massively", "outrageously", "overwhelmingly", "profoundly",
    "ridiculously", "severely", "so", "terribly", "totally", "tremendously",
    "truly", "unbearably", "utterly", "very", "wildly", "deeply", "really",
    "genuinely", "immensely", "exceptionally", "remarkably", "astoundingly",
}


def _escape(text: str) -> str:
    """Escape XML-special characters in raw text."""
    return html.escape(text, quote=False)


def _apply_word_emphasis(text: str) -> str:
    """
    Scan each whitespace-delimited token and wrap with SSML emphasis tags:
      - ALL-CAPS words (len > 1)    → <emphasis level="strong">
      - intensifier words (lowercase) → <emphasis level="moderate">
    Punctuation attached to the word is preserved outside the tag.
    """
    def replace_token(match: re.Match) -> str:
        token = match.group(0)

        # Separate leading/trailing punctuation from the core word
        lead_m  = re.match(r'^([^\w]*)(.+?)([^\w]*)$', token, re.DOTALL)
        if not lead_m:
            return token

        lead, word, trail = lead_m.groups()
        bare = _escape(word)

        if word.isupper() and len(word) > 1:
            return f'{lead}<emphasis level="strong">{bare}</emphasis>{trail}'

        lower = word.lower().strip(".,!?;:\"'")
        if lower in _INTENSIFIER_SET:
            return f'{lead}<emphasis level="moderate">{bare}</emphasis>{trail}'

        return token   # unchanged

    # Operate on each whitespace chunk
    return re.sub(r'\S+', replace_token, text)


def _apply_pause_breaks(text: str) -> str:
    """
    Insert <break> tags at natural pause points.
    Must run AFTER word emphasis so we don't corrupt tags.
    """
    # After '. ', '? ', '; ', ': ' — sentence-level pauses
    text = re.sub(r'([.;:])\s+', r'\1<break time="250ms"/> ', text)

    # After '! ' — exclamation pause
    text = re.sub(r'!\s+', r'!<break time="100ms"/> ', text)

    # After ', ' — short clause pause
    text = re.sub(r',\s+', r',<break time="75ms"/> ', text)

    return text


def build_ssml(plain_text: str, profile: "VoiceProfile") -> str:
    """
    Convert *plain_text* to an SSML document modulated for *profile*.

    Steps:
      1. Escape XML-special chars
      2. Apply word-level emphasis
      3. Insert pause breaks
      4. Wrap in <prosody> + <speak>

    Returns a valid SSML string ready for edge-tts.Communicate.
    """
    # 1 - escape
    escaped = _escape(plain_text)

    # 2 - emphasis
    emphasised = _apply_word_emphasis(escaped)

    # 3 - pauses
    with_breaks = _apply_pause_breaks(emphasised)

    # 4 - prosody wrapper (global rate/pitch/volume from the scaled profile)
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n'
        f'  <prosody rate="{profile.rate}" pitch="{profile.pitch}" volume="{profile.volume}">\n'
        f'    {with_breaks}\n'
        '  </prosody>\n'
        '</speak>'
    )

    logger.debug("Built SSML (%d chars) for emotion=%s", len(ssml), profile.emotion)
    return ssml
