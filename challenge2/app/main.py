"""
The Pitch Visualizer — FastAPI Application
==========================================
Ingests narrative text, segments it into scenes, engineers visual prompts
(via Gemini 2.0 Flash LLM or rule-based fallback), generates images via
Pollinations.ai (FLUX.1 — free), and renders a cinematic storyboard HTML page.

Bonus features:
  ✓ User-selectable visual styles (5 styles)
  ✓ LLM-powered prompt refinement via Gemini 2.0 Flash
  ✓ Visual consistency via Style DNA injected into every prompt
"""

import os
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY", "").strip() or None

import nltk
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.segmenter import segment_text
from app.prompt_engineer import engineer_prompts
from app.image_generator import generate_images
from app.storyboard import render_storyboard

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory job store  (replaced by Redis/DB for production at scale)
# ---------------------------------------------------------------------------
jobs: dict = {}


# ---------------------------------------------------------------------------
# Lifespan — download NLTK data on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Downloading NLTK tokenizer data…")
    for pkg in ("punkt", "punkt_tab", "averaged_perceptron_tagger"):
        nltk.download(pkg, quiet=True)
    logger.info("NLTK data ready.")
    yield
    logger.info("Shutting down Pitch Visualizer.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="The Pitch Visualizer",
    description=(
        "Transform narrative text into a multi-panel visual storyboard. "
        "Powered by NLTK segmentation, **Gemini 2.0 Flash** LLM prompt engineering "
        "(with rule-based fallback), visual consistency via Style DNA, "
        "and Pollinations.ai FLUX.1 image generation (free, no billing required)."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
VALID_STYLES = ["cinematic", "watercolor", "flat-illustration", "oil-painting", "digital-art"]


class StoryboardRequest(BaseModel):
    text: str
    style: Optional[str] = "cinematic"
    title: Optional[str] = "Pitch Storyboard"
    use_llm: Optional[bool] = True  # Set False to always use rule-based (faster, no quota)

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        if len(v) > 5000:
            raise ValueError("text exceeds 5000 character limit")
        return v

    @field_validator("style")
    @classmethod
    def style_valid(cls, v: str) -> str:
        if v not in VALID_STYLES:
            raise ValueError(f"style must be one of {VALID_STYLES}")
        return v


class StoryboardResponse(BaseModel):
    job_id: str
    status: str
    scene_count: int
    message: str


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------
async def process_storyboard(
    job_id: str, text: str, style: str, title: str, use_llm: bool
) -> None:
    try:
        # 1. Segment
        jobs[job_id]["status"] = "segmenting"
        scenes = segment_text(text)
        jobs[job_id]["scene_count"] = len(scenes)
        jobs[job_id]["scenes"] = scenes
        logger.info(f"[{job_id}] Segmented into {len(scenes)} scenes.")

        # 2. Engineer prompts (Gemini LLM → rule-based fallback)
        jobs[job_id]["status"] = "engineering_prompts"
        prompts = await engineer_prompts(
            scenes,
            style,
            use_llm=use_llm,
            google_api_key=GOOGLE_API_KEY,
        )
        jobs[job_id]["prompts"] = prompts
        jobs[job_id]["prompt_mode"] = "gemini" if (use_llm and GOOGLE_API_KEY) else "rule-based"
        logger.info(f"[{job_id}] Prompts engineered.")

        # 3. Generate images (concurrent)
        jobs[job_id]["status"] = "generating_images"
        images = await generate_images(prompts, job_id, jobs)
        jobs[job_id]["images"] = images
        logger.info(f"[{job_id}] Images generated.")

        # 4. Render HTML storyboard
        jobs[job_id]["status"] = "rendering"
        html = render_storyboard(
            scenes, prompts, images, style, title,
            prompt_mode=jobs[job_id]["prompt_mode"],
        )
        jobs[job_id]["html"] = html

        jobs[job_id]["status"] = "completed"
        logger.info(f"[{job_id}] Storyboard complete.")

    except Exception as exc:
        logger.exception(f"[{job_id}] Processing failed: {exc}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Pitch Visualizer</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#0a0a0f;color:#f1f5f9;font-family:'Inter',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:20px}
    .container{max-width:640px}
    h1{font-family:'Space Grotesk',sans-serif;font-size:3rem;font-weight:700;background:linear-gradient(135deg,#f1f5f9,#a5b4fc,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:12px}
    p{color:#94a3b8;font-size:1.1rem;line-height:1.7;margin-bottom:32px}
    .links{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
    a{display:inline-block;padding:12px 28px;border-radius:10px;font-weight:600;font-size:14px;text-decoration:none;transition:all .2s}
    .btn-primary{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white}
    .btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(99,102,241,.4)}
    .btn-secondary{background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.3);color:#a5b4fc}
    .btn-secondary:hover{background:rgba(99,102,241,.2)}
    .badge{display:inline-block;background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);border-radius:100px;padding:6px 16px;font-size:13px;color:#818cf8;margin-bottom:24px}
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">🎬 AI-Powered Storyboard Generator</div>
    <h1>The Pitch Visualizer</h1>
    <p>Transform narrative text into a cinematic multi-panel visual storyboard. Powered by NLTK &amp; Pollinations.ai FLUX.1 — completely free.</p>
    <div class="links">
      <a href="/docs" class="btn-primary">📖 Interactive API Docs</a>
      <a href="/redoc" class="btn-secondary">📚 ReDoc</a>
      <a href="/health" class="btn-secondary">❤️ Health Check</a>
    </div>
  </div>
</body>
</html>
    """)


@app.get("/health", tags=["Monitoring"])
async def health():
    """Liveness probe for Render health checks."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "service": "pitch-visualizer",
        "llm_available": bool(GOOGLE_API_KEY),
        "styles": VALID_STYLES,
    }


@app.post(
    "/generate-storyboard",
    response_model=StoryboardResponse,
    status_code=202,
    tags=["Storyboard"],
    summary="Submit a narrative text for storyboard generation",
)
async def generate_storyboard(request: StoryboardRequest, background_tasks: BackgroundTasks):
    """
    **Submit narrative text** to generate a visual storyboard.

    - Returns a `job_id` immediately (async job pattern).
    - Poll `GET /status/{job_id}` to track progress.
    - Fetch `GET /storyboard/{job_id}` for the final HTML page.

    **Styles**: `cinematic` | `watercolor` | `flat-illustration` | `oil-painting` | `digital-art`

    **use_llm**: Set `true` (default) to use Gemini 2.0 Flash for LLM-powered prompt
    refinement. Requires `GOOGLE_API_KEY` env var. Automatically falls back to
    rule-based engineering if the key is absent.
    """
    job_id = str(uuid.uuid4())
    llm_active = bool(request.use_llm and GOOGLE_API_KEY)
    jobs[job_id] = {
        "status": "queued",
        "text": request.text,
        "style": request.style,
        "title": request.title,
        "use_llm": request.use_llm,
        "llm_available": llm_active,
        "scene_count": 0,
        "progress": 0,
    }
    background_tasks.add_task(
        process_storyboard,
        job_id, request.text, request.style, request.title, request.use_llm,
    )
    mode_label = "Gemini 2.0 Flash" if llm_active else "rule-based (no GOOGLE_API_KEY)"
    logger.info(f"[{job_id}] Job queued — style={request.style}, prompt_mode={mode_label}")
    return StoryboardResponse(
        job_id=job_id,
        status="queued",
        scene_count=0,
        message=(
            f"Job queued (prompt_mode={mode_label}). "
            f"Poll GET /status/{job_id} to track progress."
        ),
    )


@app.get(
    "/status/{job_id}",
    tags=["Storyboard"],
    summary="Poll the status of a storyboard generation job",
)
async def get_status(job_id: str):
    """Returns status, progress percentage, scene count, and prompt mode for the job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = jobs[job_id]
    progress_map = {
        "queued": 5,
        "segmenting": 15,
        "engineering_prompts": 30,
        "generating_images": 70,
        "rendering": 90,
        "completed": 100,
        "failed": -1,
    }
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": progress_map.get(job["status"], 0),
        "scene_count": job.get("scene_count", 0),
        "prompt_mode": job.get("prompt_mode", "pending"),
        "llm_available": job.get("llm_available", False),
        "error": job.get("error"),
    }


@app.get(
    "/storyboard/{job_id}",
    response_class=HTMLResponse,
    tags=["Storyboard"],
    summary="Retrieve the completed storyboard as a self-contained HTML page",
)
async def get_storyboard(job_id: str):
    """
    Returns a fully self-contained HTML storyboard page.
    Images are embedded as base64 data URIs — no external hosting needed.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = jobs[job_id]
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error', 'unknown error')}")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=202,
            detail=f"Job not yet complete. Current status: '{job['status']}'. Poll /status/{job_id}.",
        )
    return HTMLResponse(content=job["html"])


@app.get(
    "/storyboard/{job_id}/json",
    tags=["Storyboard"],
    summary="Retrieve storyboard data as structured JSON",
)
async def get_storyboard_json(job_id: str):
    """Returns all scenes, engineered prompts, prompt mode, and image data URIs as JSON."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=202, detail=f"Status: {job['status']}")

    scenes_data = [
        {
            "scene_number": i + 1,
            "original_text": scene,
            "engineered_prompt": prompt,
            "image_data_uri": image,
        }
        for i, (scene, prompt, image) in enumerate(
            zip(job["scenes"], job["prompts"], job["images"])
        )
    ]
    return JSONResponse(
        content={
            "job_id": job_id,
            "title": job.get("title", "Pitch Storyboard"),
            "style": job["style"],
            "scene_count": job["scene_count"],
            "prompt_mode": job.get("prompt_mode", "rule-based"),
            "llm_available": job.get("llm_available", False),
            "scenes": scenes_data,
        }
    )


@app.get("/styles", tags=["Storyboard"], summary="List available visual styles")
async def list_styles():
    """Returns all supported visual styles with descriptions."""
    from app.llm_enhancer import STYLE_DNA
    return {
        "styles": [
            {"id": s, "description": STYLE_DNA.get(s, "").split(",")[0]}
            for s in VALID_STYLES
        ],
        "llm_available": bool(GOOGLE_API_KEY),
        "llm_model": "gemini-2.0-flash" if GOOGLE_API_KEY else None,
    }
