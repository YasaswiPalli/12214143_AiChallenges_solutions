"""
image_generator.py
==================
Generates images via Pollinations.ai — a completely FREE image generation
API powered by FLUX.1 and Stable Diffusion XL.

No API key required. No sign-up required. No cost.
Docs: https://pollinations.ai
"""

import asyncio
import base64
import logging
import urllib.parse
from typing import List

import httpx

logger = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

# Image dimensions (16:9 aspect ratio — ideal for storyboard panels)
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720

# Fallback model if flux fails
MODELS = ["flux", "turbo"]  # flux = FLUX.1-schnell (best free model)

MAX_RETRIES = 4
TIMEOUT_SECONDS = 90.0  # Pollinations can be slow under load
RATE_LIMIT_DELAY_SECONDS = 8.0
REQUEST_SPACING_SECONDS = 4.0


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    """Prefer provider Retry-After hints, otherwise back off more on rate limits."""
    if response is not None and response.status_code == 429:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(float(retry_after), RATE_LIMIT_DELAY_SECONDS)
            except ValueError:
                pass
        return RATE_LIMIT_DELAY_SECONDS * attempt
    return float(2 ** attempt)


async def _fetch_single_image(
    client: httpx.AsyncClient,
    prompt: str,
    seed: int,
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> str:
    """
    Fetch a single image from Pollinations.ai.
    Returns a base64-encoded data URI string.
    Retries up to MAX_RETRIES times with exponential backoff.
    Tries FLUX first, then turbo as fallback.
    """
    encoded_prompt = urllib.parse.quote(prompt, safe="")

    for model in MODELS:
        url = f"{POLLINATIONS_BASE}/{encoded_prompt}"
        params = {
            "width": width,
            "height": height,
            "model": model,
            "seed": seed,
            "nologo": "true",
            "enhance": "true",
            "safe": "true",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Fetching image (model={model}, attempt={attempt}, seed={seed})")
                response = await client.get(
                    url,
                    params=params,
                    timeout=TIMEOUT_SECONDS,
                    follow_redirects=True,
                )
                response.raise_for_status()

                content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                img_b64 = base64.b64encode(response.content).decode("utf-8")
                return f"data:{content_type};base64,{img_b64}"

            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt} (model={model}).")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(_retry_delay(None, attempt))
            except httpx.HTTPStatusError as exc:
                logger.warning(f"HTTP {exc.response.status_code} on attempt {attempt} (model={model}).")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(_retry_delay(exc.response, attempt))
            except Exception as exc:
                logger.error(f"Unexpected error on attempt {attempt}: {exc}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(_retry_delay(None, attempt))

    # All models / retries exhausted — return SVG placeholder
    logger.error(f"All retries exhausted for seed={seed}. Using placeholder.")
    return _placeholder_svg(f"Scene {seed % 1000} — image generation temporarily unavailable")


async def generate_images(
    prompts: List[str],
    job_id: str,
    jobs: dict,
) -> List[str]:
    """
    Generate images for all prompts with light throttling.
    Updates the job's progress field as images complete.
    """
    async with httpx.AsyncClient(
        headers={"User-Agent": "PitchVisualizer/1.0 (https://github.com/pitch-visualizer)"},
    ) as client:
        images: List[str] = []
        completed = 0
        total = len(prompts)

        for i, prompt in enumerate(prompts):
            if i > 0:
                await asyncio.sleep(REQUEST_SPACING_SECONDS)

            try:
                image = await _fetch_single_image(
                    client,
                    prompt,
                    seed=abs(hash(f"{job_id}-scene-{i}")) % 2_147_483_647,
                )
            except Exception as exc:
                logger.error(f"Image task raised: {exc}")
                image = _placeholder_svg(str(exc)[:80])

            images.append(image)
            completed += 1
            if jobs and job_id in jobs:
                # Progress: 30% (after prompts) → 90% (before render)
                jobs[job_id]["progress"] = 30 + int((completed / total) * 60)

        return images


# ---------------------------------------------------------------------------
# SVG Placeholder
# ---------------------------------------------------------------------------
def _placeholder_svg(message: str = "Image unavailable") -> str:
    """Return a styled SVG placeholder as a base64 data URI."""
    safe_message = message[:70].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{IMAGE_WIDTH}" height="{IMAGE_HEIGHT}" viewBox="0 0 {IMAGE_WIDTH} {IMAGE_HEIGHT}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f0f1a"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#6366f1"/>
      <stop offset="100%" style="stop-color:#8b5cf6"/>
    </linearGradient>
  </defs>
  <rect width="{IMAGE_WIDTH}" height="{IMAGE_HEIGHT}" fill="url(#bg)"/>
  <rect x="0" y="{IMAGE_HEIGHT - 4}" width="{IMAGE_WIDTH}" height="4" fill="url(#accent)" opacity="0.6"/>
  <circle cx="{IMAGE_WIDTH//2}" cy="{IMAGE_HEIGHT//2 - 40}" r="36" fill="none" stroke="#6366f1" stroke-width="2" opacity="0.4"/>
  <text x="{IMAGE_WIDTH//2}" y="{IMAGE_HEIGHT//2 - 28}" text-anchor="middle" fill="#6366f1" font-size="32" font-family="Arial">🎬</text>
  <text x="{IMAGE_WIDTH//2}" y="{IMAGE_HEIGHT//2 + 20}" text-anchor="middle" fill="#8892b0" font-size="18" font-family="Arial, sans-serif">Generating visual scene…</text>
  <text x="{IMAGE_WIDTH//2}" y="{IMAGE_HEIGHT//2 + 52}" text-anchor="middle" fill="#475569" font-size="13" font-family="Arial, sans-serif">{safe_message}</text>
</svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"
