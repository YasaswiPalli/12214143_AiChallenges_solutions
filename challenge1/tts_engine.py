"""
tts_engine.py
─────────────
Wraps Microsoft Edge TTS (edge-tts library) to generate audio with
dynamic vocal-parameter modulation based on detected emotion.

Feature ③ — SSML Integration: the plain text is first converted to an
SSML document (via ssml_builder.py) before being passed to edge-tts,
enabling word-level emphasis and natural pause breaks.
"""

from __future__ import annotations
import logging
import tempfile
from pathlib import Path

import edge_tts  # type: ignore

from emotion_detector import VoiceProfile
from ssml_builder import build_ssml

logger = logging.getLogger(__name__)

# Default voice (en-US, female, neural — sounds natural)
DEFAULT_VOICE = "en-US-AriaNeural"

# Voices per emotion — seven categories now
EMOTION_VOICES: dict[str, str] = {
    "joy":      "en-US-JennyNeural",        # warm / friendly
    "love":     "en-US-AriaNeural",         # gentle / intimate
    "surprise": "en-US-JennyNeural",        # bright / animated
    "sadness":  "en-US-AriaNeural",         # empathetic / soft
    "anger":    "en-US-GuyNeural",          # firm / assertive
    "fear":     "en-US-AriaNeural",         # tense / urgent
    "neutral":  "en-US-ChristopherNeural",  # balanced / professional
}


async def _synthesize_async(
    ssml: str,
    voice: str,
    output_path: Path,
) -> None:
    """Internal coroutine: call edge-tts with SSML and write audio to *output_path*."""
    communicate = edge_tts.Communicate(
        text=ssml,
        voice=voice,
        # Note: rate/pitch/volume are already embedded inside the SSML <prosody> tag,
        # so we pass neutral defaults here to avoid double-applying them.
        rate="+0%",
        pitch="+0Hz",
        volume="+0%",
    )

    logger.info("Synthesizing SSML | voice=%s | %d chars", voice, len(ssml))
    await communicate.save(str(output_path))
    logger.info("Audio saved → %s", output_path)


async def synthesize_speech(text: str, profile: VoiceProfile) -> bytes:
    """
    Convert *text* to expressive MP3 audio using *profile*:
      1. Build SSML document (emphasis + pauses + prosody wrapper)
      2. Synthesise via edge-tts neural voice
      3. Return raw MP3 bytes

    Raises RuntimeError on failure.
    """
    voice = EMOTION_VOICES.get(profile.emotion, DEFAULT_VOICE)
    ssml  = build_ssml(text, profile)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        await _synthesize_async(ssml, voice, tmp_path)
        audio_bytes = tmp_path.read_bytes()
        return audio_bytes
    except Exception as exc:
        logger.exception("TTS synthesis failed.")
        raise RuntimeError(f"TTS synthesis failed: {exc}") from exc
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
