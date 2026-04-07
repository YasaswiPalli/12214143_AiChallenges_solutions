"""
emotion_detector.py
───────────────────
Classifies text into one of SEVEN emotional categories using a lightweight
DistilBERT model fine-tuned on the GoEmotions dataset.

Bonus features implemented:
  ① Granular Emotions  — 7 distinct buckets (added love, surprise)
  ② Intensity Scaling  — vocal parameters are dynamically scaled based on
                         a composite intensity score (model confidence +
                         punctuation signals + intensifier words)

Emotion → Base Voice-parameter mapping
───────────────────────────────────────
  joy      → rate +22%,  pitch +10Hz, volume +10%
  love     → rate  -5%,  pitch  +8Hz, volume  -5%
  surprise → rate +28%,  pitch +18Hz, volume +12%
  sadness  → rate -25%,  pitch  -8Hz, volume -15%
  anger    → rate +15%,  pitch  -5Hz, volume +25%
  fear     → rate +30%,  pitch +15Hz, volume  +5%
  neutral  → rate   0%,  pitch   0Hz, volume   0%

Intensity tiers scale the base values:
  low    (score < 0.40) → × 0.5
  medium (0.40–0.70)    → × 1.0
  high   (score > 0.70) → × 1.6
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Intensifier word list used for intensity scoring
# ─────────────────────────────────────────────────────────
_INTENSIFIERS = {
    "absolutely", "completely", "entirely", "extremely", "incredibly",
    "insanely", "massively", "outrageously", "overwhelmingly", "profoundly",
    "ridiculously", "severely", "so", "terribly", "totally", "tremendously",
    "truly", "unbearably", "utterly", "very", "wildly", "deeply", "really",
    "genuinely", "immensely", "exceptionally", "remarkably", "astoundingly",
}


# ─────────────────────────────────────────────────────────
# Voice-parameter dataclass
# ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VoiceProfile:
    """Vocal parameters passed to edge-tts."""
    emotion: str
    rate: str       # e.g. "+22%"  (edge-tts format)
    pitch: str      # e.g. "+10Hz" (edge-tts format)
    volume: str     # e.g. "+10%"  (edge-tts format)
    description: str
    # Raw numeric bases (used for intensity scaling)
    _rate_val: float = 0.0    # percentage integer value, e.g. 22.0
    _pitch_val: float = 0.0   # Hz integer value, e.g. 10.0
    _volume_val: float = 0.0  # percentage integer value, e.g. 10.0


# ─────────────────────────────────────────────────────────
# Helper: parse edge-tts param strings → float
# ─────────────────────────────────────────────────────────
def _pct(s: str) -> float:
    """'+22%' → 22.0,  '-25%' → -25.0"""
    return float(s.replace("%", ""))

def _hz(s: str) -> float:
    """'+10Hz' → 10.0,  '-8Hz' → -8.0"""
    return float(s.replace("Hz", ""))

def _fmt_pct(v: float) -> str:
    return f"+{v:.0f}%" if v >= 0 else f"{v:.0f}%"

def _fmt_hz(v: float) -> str:
    return f"+{v:.0f}Hz" if v >= 0 else f"{v:.0f}Hz"


# ─────────────────────────────────────────────────────────
# Base emotion profiles  (seven categories)
# ─────────────────────────────────────────────────────────
def _make(emotion: str, rate: str, pitch: str, volume: str, desc: str) -> VoiceProfile:
    return VoiceProfile(
        emotion=emotion,
        rate=rate, pitch=pitch, volume=volume,
        description=desc,
        _rate_val=_pct(rate), _pitch_val=_hz(pitch), _volume_val=_pct(volume),
    )


EMOTION_PROFILES: dict[str, VoiceProfile] = {
    "joy": _make(
        "joy", "+22%", "+10Hz", "+10%",
        "Upbeat, enthusiastic, warm delivery",
    ),
    "love": _make(
        "love", "-5%", "+8Hz", "-5%",
        "Tender, soft, intimate, heartfelt delivery",
    ),
    "surprise": _make(
        "surprise", "+28%", "+18Hz", "+12%",
        "Bright, wide-eyed, animated delivery",
    ),
    "sadness": _make(
        "sadness", "-25%", "-8Hz", "-15%",
        "Slow, empathetic, gentle delivery",
    ),
    "anger": _make(
        "anger", "+15%", "-5Hz", "+25%",
        "Firm, assertive, forceful delivery",
    ),
    "fear": _make(
        "fear", "+30%", "+15Hz", "+5%",
        "Rapid, tense, urgent delivery",
    ),
    "neutral": _make(
        "neutral", "+0%", "+0Hz", "+0%",
        "Balanced, clear, measured delivery",
    ),
}


# ─────────────────────────────────────────────────────────
# Model label → our 7 buckets
# ─────────────────────────────────────────────────────────
_LABEL_MAP: dict[str, str] = {
    "joy":      "joy",
    "love":     "love",       # ① now its own category
    "surprise": "surprise",   # ① now its own category
    "sadness":  "sadness",
    "anger":    "anger",
    "fear":     "fear",
}


# ─────────────────────────────────────────────────────────
# ② Intensity scoring
# ─────────────────────────────────────────────────────────
def score_intensity(text: str, confidence: float) -> float:
    """
    Compute a 0.0–1.0 intensity score using three signals:

    1. Model confidence  (weight 40%)
    2. Punctuation cues  (weight 30%): !, ALL-CAPS words
    3. Intensifier words (weight 30%): "extremely", "so", "absolutely"…

    Returns a value in [0.0, 1.0].
    """
    words = text.split()
    total = max(len(words), 1)

    # — signal 1: model confidence
    sig_confidence = confidence  # already in [0, 1]

    # — signal 2: punctuation signals (capped at 1.0)
    exclamations = text.count("!")
    questions    = text.count("?")
    caps_words   = sum(1 for w in words if w.isupper() and len(w) > 1)
    punctuation_raw = (exclamations * 0.4 + questions * 0.2 + caps_words * 0.3) / total
    sig_punctuation = min(punctuation_raw * 3.0, 1.0)   # scale & cap

    # — signal 3: intensifier density (capped at 1.0)
    lower_words = [w.strip(".,!?;:\"'").lower() for w in words]
    intensifier_count = sum(1 for w in lower_words if w in _INTENSIFIERS)
    sig_intensifiers = min(intensifier_count / max(total * 0.15, 1), 1.0)

    score = (
        0.40 * sig_confidence +
        0.30 * sig_punctuation +
        0.30 * sig_intensifiers
    )
    logger.debug(
        "Intensity | conf=%.3f punct=%.3f intens=%.3f → total=%.3f",
        sig_confidence, sig_punctuation, sig_intensifiers, score,
    )
    return round(min(max(score, 0.0), 1.0), 4)


def intensity_tier(score: float) -> str:
    if score < 0.40:
        return "low"
    if score < 0.70:
        return "medium"
    return "high"


def scale_profile(profile: VoiceProfile, intensity: float) -> VoiceProfile:
    """
    Return a new VoiceProfile with rate/pitch/volume scaled by intensity.

    Scaling factors:
      low    (< 0.40) → 0.5×
      medium (< 0.70) → 1.0×
      high   (≥ 0.70) → 1.6×
    """
    factor = 0.5 if intensity < 0.40 else (1.6 if intensity >= 0.70 else 1.0)

    new_rate   = profile._rate_val   * factor
    new_pitch  = profile._pitch_val  * factor
    new_volume = profile._volume_val * factor

    return VoiceProfile(
        emotion=profile.emotion,
        rate=_fmt_pct(new_rate),
        pitch=_fmt_hz(new_pitch),
        volume=_fmt_pct(new_volume),
        description=profile.description,
        _rate_val=new_rate,
        _pitch_val=new_pitch,
        _volume_val=new_volume,
    )


# ─────────────────────────────────────────────────────────
# Model loader
# ─────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_pipeline():
    from transformers import pipeline  # type: ignore
    logger.info("Loading emotion classification model …")
    pipe = pipeline(
        "text-classification",
        model="bhadresh-savani/distilbert-base-uncased-emotion",
        top_k=1,
        truncation=True,
        max_length=512,
    )
    logger.info("Emotion model loaded ✓")
    return pipe


# ─────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────
def detect_emotion(
    text: str,
) -> tuple[str, float, float, str, VoiceProfile]:
    """
    Classify *text* and return:
        (emotion, confidence, intensity_score, intensity_tier, scaled_VoiceProfile)

    Falls back to 'neutral' on error.
    """
    try:
        pipe = _load_pipeline()
        results = pipe(text)
        top = results[0][0] if isinstance(results[0], list) else results[0]
        raw_label: str  = top["label"].lower()
        confidence: float = float(top["score"])

        mapped  = _LABEL_MAP.get(raw_label, "neutral")
        base_profile = EMOTION_PROFILES[mapped]

        intensity = score_intensity(text, confidence)
        tier      = intensity_tier(intensity)
        scaled    = scale_profile(base_profile, intensity)

        logger.debug(
            "emotion=%s raw=%s conf=%.3f intensity=%.3f tier=%s",
            mapped, raw_label, confidence, intensity, tier,
        )
        return mapped, confidence, intensity, tier, scaled

    except Exception as exc:
        logger.warning("Emotion detection failed (%s); defaulting to neutral.", exc)
        neutral = EMOTION_PROFILES["neutral"]
        return "neutral", 0.0, 0.5, "medium", neutral
