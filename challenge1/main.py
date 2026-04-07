"""
main.py  –  The Empathy Engine  (FastAPI)
─────────────────────────────────────────
Endpoints
─────────
  GET  /              → health check / API info
  GET  /emotions      → list supported emotions & voice profiles
  POST /synthesize    → detect emotion + generate modulated speech
  POST /synthesize/{emotion} → force a specific emotion (testing)

Deploy to Render
────────────────
  Build command   : pip install -r requirements.txt
  Start command   : uvicorn main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations
import logging
import time
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from emotion_detector import detect_emotion, EMOTION_PROFILES
from tts_engine import synthesize_speech

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("empathy_engine")


# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────
app = FastAPI(
    title="The Empathy Engine",
    description=(
        "An AI service that detects the emotional tone of text and synthesizes "
        "expressive, human-like speech with dynamically modulated vocal parameters "
        "(rate, pitch, volume) mapped to the detected emotion."
    ),
    version="1.0.0",
    contact={
        "name": "Empathy Engine API",
    },
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────
class SynthesizeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        description="The text to analyze and convert to speech.",
        examples=["I'm so thrilled about this amazing opportunity!"],
    )


class EmotionInfo(BaseModel):
    emotion: str
    rate: str
    pitch: str
    volume: str
    description: str
    voice: str


class SynthesisMetadata(BaseModel):
    text: str
    detected_emotion: str
    confidence: float
    voice_profile: EmotionInfo
    processing_time_ms: float
    audio_format: str = "audio/mpeg"
    audio_size_bytes: int


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """API health check and service overview."""
    return {
        "service": "The Empathy Engine",
        "status": "online",
        "version": "1.0.0",
        "description": (
            "Emotion-aware Text-to-Speech synthesis. "
            "Send text → get modulated human-like speech audio."
        ),
        "endpoints": {
            "health":      "GET /",
            "emotions":    "GET /emotions",
            "synthesize":  "POST /synthesize",
            "forced_emotion": "POST /synthesize/{emotion}",
            "docs":        "GET /docs",
            "openapi":     "GET /openapi.json",
        },
    }


@app.get("/emotions", tags=["Emotions"], response_model=dict)
async def list_emotions():
    """Return all 7 supported emotion categories and their base voice configurations."""
    from tts_engine import EMOTION_VOICES, DEFAULT_VOICE

    result = {}
    for name, profile in EMOTION_PROFILES.items():
        result[name] = {
            "emotion":     profile.emotion,
            "rate":        profile.rate,
            "pitch":       profile.pitch,
            "volume":      profile.volume,
            "description": profile.description,
            "voice":       EMOTION_VOICES.get(name, DEFAULT_VOICE),
            "note":        "These are base values; actual audio uses intensity-scaled parameters.",
        }
    return result


@app.post(
    "/synthesize",
    tags=["Synthesis"],
    summary="Detect emotion and synthesize modulated speech",
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio with emotion-modulated vocal parameters.",
        },
        422: {"description": "Validation error"},
        500: {"description": "TTS synthesis error"},
    },
)
async def synthesize(
    request: SynthesizeRequest,
    metadata: Annotated[
        bool,
        Query(description="If true, return JSON metadata instead of audio bytes."),
    ] = False,
):
    """
    **Core endpoint** — The Empathy Engine pipeline:

    1. **Emotion Detection**: Classifies the input text using a DistilBERT model
       fine-tuned on GoEmotions (6 classes → 5 buckets: joy, sadness, anger, fear, neutral).
    2. **Voice Profile Selection**: Maps the detected emotion to a pre-defined
       vocal parameter configuration (rate, pitch, volume + TTS voice).
    3. **Speech Synthesis**: Generates modulated MP3 audio via Microsoft Edge
       TTS neural voices — no API key required.

    Returns the raw MP3 audio by default.  Set `?metadata=true` to receive a
    JSON report instead (useful for testing without an audio player).
    """
    t0 = time.perf_counter()

    # Step 1 – detect emotion + intensity
    try:
        emotion, confidence, intensity, tier, profile = detect_emotion(request.text)
    except Exception as exc:
        logger.exception("Emotion detection failed.")
        raise HTTPException(status_code=500, detail=f"Emotion detection error: {exc}")

    # Step 2 – synthesize speech with SSML
    try:
        audio_bytes = await synthesize_speech(request.text, profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "Request complete | emotion=%s conf=%.2f intensity=%.2f(%s) size=%d bytes time=%.0fms",
        emotion, confidence, intensity, tier, len(audio_bytes), elapsed_ms,
    )

    # Step 3 – respond
    if metadata:
        from tts_engine import EMOTION_VOICES, DEFAULT_VOICE
        return JSONResponse(
            content={
                "text":              request.text,
                "detected_emotion":  emotion,
                "confidence":        round(confidence, 4),
                "intensity_score":   round(intensity, 4),
                "intensity_tier":    tier,
                "voice_profile": {
                    "emotion":     profile.emotion,
                    "rate":        profile.rate,
                    "pitch":       profile.pitch,
                    "volume":      profile.volume,
                    "description": profile.description,
                    "voice":       EMOTION_VOICES.get(emotion, DEFAULT_VOICE),
                },
                "ssml_enabled":       True,
                "processing_time_ms": round(elapsed_ms, 1),
                "audio_format":       "audio/mpeg",
                "audio_size_bytes":   len(audio_bytes),
            }
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "X-Detected-Emotion":   emotion,
            "X-Emotion-Confidence": str(round(confidence, 4)),
            "X-Intensity-Score":    str(round(intensity, 4)),
            "X-Intensity-Tier":     tier,
            "X-Voice-Rate":         profile.rate,
            "X-Voice-Pitch":        profile.pitch,
            "X-Voice-Volume":       profile.volume,
            "X-Processing-Time-Ms": str(round(elapsed_ms, 1)),
            "Content-Disposition":  f'attachment; filename="empathy_{emotion}.mp3"',
        },
    )


@app.post(
    "/synthesize/{emotion}",
    tags=["Synthesis"],
    summary="Synthesize with a forced emotion (for testing/demo)",
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 audio."},
        400: {"description": "Unknown emotion label"},
        500: {"description": "TTS synthesis error"},
    },
)
async def synthesize_forced_emotion(
    emotion: str,
    request: SynthesizeRequest,
    metadata: Annotated[
        bool,
        Query(description="Return JSON metadata instead of audio bytes."),
    ] = False,
):
    """
    Bypass emotion detection and **force a specific emotion** for synthesis.

    Useful for:
    - Demonstrating each emotion's vocal profile side-by-side
    - Testing voice parameter mappings without relying on the classifier

    Valid emotions: `joy`, `sadness`, `anger`, `fear`, `neutral`
    """
    emotion = emotion.lower().strip()
    if emotion not in EMOTION_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown emotion '{emotion}'. "
                f"Valid options: {list(EMOTION_PROFILES.keys())}"
            ),
        )

    t0 = time.perf_counter()
    base_profile = EMOTION_PROFILES[emotion]

    # Still apply intensity scaling even for forced emotion
    from emotion_detector import score_intensity, intensity_tier, scale_profile
    intensity  = score_intensity(request.text, 1.0)
    tier       = intensity_tier(intensity)
    profile    = scale_profile(base_profile, intensity)

    try:
        audio_bytes = await synthesize_speech(request.text, profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed_ms = (time.perf_counter() - t0) * 1000

    if metadata:
        from tts_engine import EMOTION_VOICES, DEFAULT_VOICE
        return JSONResponse(
            content={
                "text":             request.text,
                "forced_emotion":   emotion,
                "intensity_score":  round(intensity, 4),
                "intensity_tier":   tier,
                "voice_profile": {
                    "emotion":     profile.emotion,
                    "rate":        profile.rate,
                    "pitch":       profile.pitch,
                    "volume":      profile.volume,
                    "description": profile.description,
                    "voice":       EMOTION_VOICES.get(emotion, DEFAULT_VOICE),
                },
                "ssml_enabled":       True,
                "processing_time_ms": round(elapsed_ms, 1),
                "audio_format":       "audio/mpeg",
                "audio_size_bytes":   len(audio_bytes),
            }
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "X-Forced-Emotion":     emotion,
            "X-Intensity-Score":    str(round(intensity, 4)),
            "X-Intensity-Tier":     tier,
            "X-Voice-Rate":         profile.rate,
            "X-Voice-Pitch":        profile.pitch,
            "X-Voice-Volume":       profile.volume,
            "X-Processing-Time-Ms": str(round(elapsed_ms, 1)),
            "Content-Disposition":  f'attachment; filename="empathy_{emotion}.mp3"',
        },
    )
