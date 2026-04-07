"""
llm_enhancer.py
===============
Google Gemini 2.0 Flash-powered prompt refinement.

Free tier limits (no billing required):
  - 15 requests per minute
  - 1,000,000 tokens per minute
  - 1,500 requests per day

Get a free API key at: https://aistudio.google.com/apikey
Set it as GOOGLE_API_KEY in your .env file or Render environment variables.

If GOOGLE_API_KEY is not set, this module gracefully returns None and the
caller falls back to the rule-based prompt_engineer.
"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Style DNA ──────────────────────────────────────────────────────────────
# Each style has a "DNA" — a consistent visual language injected into every
# scene prompt. This ensures visual cohesion across the storyboard panels.
STYLE_DNA: dict[str, str] = {
    "cinematic": (
        "Maintain strict visual consistency: ARRI Alexa film aesthetic, "
        "warm golden-teal color grade (shadows teal, highlights warm amber), "
        "anamorphic lens with subtle flares, 2.39:1 aspect-ratio crop feel, "
        "shallow depth of field, cinematic grain overlay"
    ),
    "watercolor": (
        "Maintain strict visual consistency: soft wet-on-wet watercolor technique, "
        "warm amber-to-indigo palette, Fabriano cotton paper texture, "
        "blooming pigment edges, impressionistic loose brushwork, "
        "consistent light source from upper-left"
    ),
    "flat-illustration": (
        "Maintain strict visual consistency: Material Design 3 color system, "
        "bold Pantone-inspired flat palette with a #6366F1 indigo accent, "
        "uniform 3px geometric stroke weight, clean isometric grid, "
        "no gradients — solid fills only, Dribbble editorial style"
    ),
    "oil-painting": (
        "Maintain strict visual consistency: Dutch Golden Age palette "
        "(raw umber, ivory, ochre, deep crimson), Rembrandt 3:1 lighting ratio, "
        "thick impasto brushstrokes with palette knife texture, "
        "varnished museum finish, candlelight warmth"
    ),
    "digital-art": (
        "Maintain strict visual consistency: cyberpunk neon-noir palette "
        "(electric indigo #4F46E5, magenta #EC4899, dark navy #0A0A1A), "
        "Unreal Engine 5 Lumen ray-tracing aesthetic, volumetric atmospheric fog, "
        "sharp specular highlights, ArtStation concept-art composition"
    ),
}

# ── Scene position camera angles ───────────────────────────────────────────
CAMERA_ANGLES = [
    "wide establishing shot",
    "intimate close-up",
    "medium shot",
    "dramatic low-angle shot",
    "aerial bird's-eye view",
    "sweeping tracking shot",
    "over-the-shoulder perspective",
    "extreme close-up detail shot",
]

# ── Gemini system prompt ───────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite visual director and AI image prompt engineer with 20 years of experience in cinema, commercial photography, and digital art.

Your job: Transform a plain narrative sentence into a single, richly detailed image generation prompt for FLUX.1.

STRICT RULES:
1. Output ONLY the final prompt — no explanation, no markdown formatting, no preamble
2. Make it intensely visual and descriptive (subject, environment, lighting, mood, textures, atmosphere)
3. Incorporate the specified camera angle naturally
4. Apply the style DNA consistently — this ensures visual coherence across the storyboard
5. Never include: text overlays, watermarks, logos, words, letters, UI elements
6. Keep the prompt under 180 words
7. End with: "no text, no watermark, no logo, no words"
"""


def get_api_key() -> Optional[str]:
    """Retrieve GOOGLE_API_KEY from environment. Returns None if not set."""
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    return key if key else None


async def enhance_prompt_with_gemini(
    scene: str,
    style: str,
    scene_index: int,
    api_key: str,
) -> Optional[str]:
    """
    Use Gemini 2.0 Flash to generate a rich, visually detailed image prompt
    from a plain narrative sentence.

    Returns the enhanced prompt string, or None on failure (caller falls back
    to rule-based engineering).
    """
    style_dna = STYLE_DNA.get(style, STYLE_DNA["cinematic"])
    camera = CAMERA_ANGLES[scene_index % len(CAMERA_ANGLES)]

    user_message = (
        f'Narrative sentence: "{scene}"\n\n'
        f"Visual style: {style}\n"
        f"Style DNA (apply to maintain consistency): {style_dna}\n"
        f"Camera angle for this scene: {camera}\n\n"
        f"Generate the image prompt now:"
    )

    try:
        import google.generativeai as genai  # lazy import

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )

        # Run the synchronous Gemini call in a thread pool
        response = await asyncio.to_thread(
            model.generate_content,
            user_message,
            generation_config=genai.types.GenerationConfig(
                temperature=0.85,
                max_output_tokens=300,
                candidate_count=1,
            ),
        )

        text = response.text.strip()
        if text:
            logger.info(f"Gemini enhanced scene {scene_index + 1}: {text[:80]}…")
            return text
        return None

    except Exception as exc:
        logger.warning(f"Gemini enhancement failed for scene {scene_index + 1}: {exc}")
        return None


async def enhance_all_prompts(
    scenes: list[str],
    style: str,
    api_key: str,
) -> list[Optional[str]]:
    """
    Run Gemini enhancement for all scenes concurrently.
    Returns a list of prompts (None entries mean fallback to rule-based).
    """
    tasks = [
        enhance_prompt_with_gemini(scene, style, i, api_key)
        for i, scene in enumerate(scenes)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning(f"Gemini task exception: {r}")
            processed.append(None)
        else:
            processed.append(r)
    return processed
