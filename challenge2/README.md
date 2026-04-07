# 🎬 The Pitch Visualizer

> Transform narrative text into a multi-panel visual storyboard — powered by NLTK, intelligent prompt engineering, and Pollinations.ai FLUX.1.
> **100% free. No API keys required.**

## Features

- **Bonus: Visual consistency** - style DNA is injected into every generated prompt.
- **Bonus: User-selectable styles** - cinematic, watercolor, flat illustration, oil painting, and digital art.
- **Bonus: LLM-powered prompt refinement** - optional Gemini 2.0 Flash enhancement with rule-based fallback.

- 🧠 **NLTK sentence segmentation** with smart merge & expand logic
- ✍️ **Intelligent rule-based prompt engineering** — 30+ keyword patterns, 5 visual styles, tone detection
- 🎨 **FLUX.1 image generation** via Pollinations.ai (free, no sign-up)
- 🖼️ **Self-contained storyboard HTML** — images embedded as base64 data URIs
- ⚡ **Async concurrent image generation** with retry logic
- 🚀 **AsyncJob pattern** — instant response, poll for completion
- 🌐 **Ready to deploy on Render** (free tier compatible)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Landing page |
| `GET`  | `/health` | Liveness probe |
| `POST` | `/generate-storyboard` | Submit text → returns `job_id` |
| `GET`  | `/status/{job_id}` | Poll job progress |
| `GET`  | `/storyboard/{job_id}` | Get HTML storyboard |
| `GET`  | `/storyboard/{job_id}/json` | Get JSON storyboard data |
| `GET`  | `/styles` | List supported styles and LLM availability |
| `GET`  | `/docs` | Swagger UI |
| `GET`  | `/redoc` | ReDoc |

## Quick Start

### 1. Clone & Install
```bash
git clone <your-repo-url>
cd Challenge2
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger
```

### 2. Run Locally
Optional Gemini setup:
```bash
cp .env.example .env
# Set GOOGLE_API_KEY in .env to enable LLM-powered prompt refinement.
# Leave it unset to use the free rule-based fallback.
```

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Generate a Storyboard
```bash
# Step 1: Submit text
curl -X POST http://localhost:8000/generate-storyboard \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Our company was facing a major challenge: manual sales processes were costing us 20 hours per week. We integrated an AI-powered CRM that automated lead scoring and follow-ups. Within 90 days, our close rate increased by 45% and our team could focus entirely on building customer relationships. The results exceeded all projections, making us the top-performing region in Q3.",
    "style": "cinematic",
    "title": "Sales Transformation Story",
    "use_llm": true
  }'

# Returns: {"job_id": "abc-123", "status": "queued", ...}

# Step 2: Poll status
curl http://localhost:8000/status/abc-123

# Step 3: Get HTML storyboard (when status = "completed")
curl http://localhost:8000/storyboard/abc-123 -o storyboard.html
open storyboard.html
```

## Visual Styles

| Style | Description |
|-------|-------------|
| `cinematic` | Photorealistic, ARRI Alexa, golden hour lighting |
| `watercolor` | Soft washes, impressionistic, vibrant pigments |
| `flat-illustration` | Bold vectors, geometric, Dribbble-style |
| `oil-painting` | Dutch Golden Age, chiaroscuro, impasto |
| `digital-art` | ArtStation concept art, neon, Unreal Engine |

## Deploy to Render

1. Push to GitHub:
```bash
git init
git add .
git commit -m "feat: initial Pitch Visualizer implementation"
git remote add origin <your-github-repo-url>
git push -u origin main
```

2. Go to [render.com](https://render.com) → **New Web Service** → connect your GitHub repo
3. Render auto-detects `render.yaml` — click **Deploy**
4. No environment variables are required for the default flow because Pollinations.ai is keyless.
5. Optional: set `GOOGLE_API_KEY` in Render to enable Gemini 2.0 Flash prompt refinement.

## Architecture

```
POST /generate-storyboard
         │
         ▼ asyncio BackgroundTask
[1] NLTK Sentence Tokenizer
    ↳ merge short fragments, cap at 8 scenes
         │
         ▼
[2] Rule-Based Prompt Engineer
    ↳ 30+ keyword patterns → visual descriptors
    ↳ tone detection (6 emotional tones)
    ↳ positional camera descriptors
    ↳ style preset injection
         │
         ▼
[3] Pollinations.ai FLUX.1 (concurrent asyncio.gather)
    ↳ 16:9 1280×720 images
    ↳ 3-retry exponential backoff
    ↳ SVG placeholder on failure
         │
         ▼
[4] Jinja2 Storyboard Renderer
    ↳ Self-contained HTML (base64 images)
    ↳ Dark cinematic design, scroll animations
    ↳ Timeline navigation, prompt inspector
```

## Tech Stack

- **FastAPI** — async web framework
- **NLTK** — natural language tokenization  
- **httpx** — async HTTP client for image fetching
- **Jinja2** — HTML template rendering
- **Pollinations.ai** — free FLUX.1 image generation
- **uvicorn** — ASGI server
