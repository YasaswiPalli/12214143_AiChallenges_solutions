# 🎙️ The Empathy Engine

> **Challenge 1** — Dynamic emotion-aware Text-to-Speech synthesis via FastAPI

---

## What It Does

The Empathy Engine is a REST API service that:

1. **Accepts text input** via an HTTP POST request
2. **Detects emotion** using a fine-tuned DistilBERT model (5 categories)
3. **Maps emotion → vocal parameters** (rate, pitch, volume + neural voice)
4. **Synthesizes expressive speech** via Microsoft Edge TTS neural voices
5. **Returns an MP3 audio file** ready to play

---

## Emotion → Voice Parameter Mapping

| Emotion | Rate   | Pitch   | Volume  | Voice         | Style                        |
|---------|--------|---------|---------|---------------|------------------------------|
| Joy     | +22%   | +10 Hz  | +10%    | JennyNeural   | Upbeat, enthusiastic, warm   |
| Sadness | -25%   | -8 Hz   | -15%    | AriaNeural    | Slow, empathetic, gentle     |
| Anger   | +15%   | -5 Hz   | +25%    | GuyNeural     | Firm, assertive, forceful    |
| Fear    | +30%   | +15 Hz  | +5%     | AriaNeural    | Rapid, tense, urgent         |
| Neutral |  +0%   |  +0 Hz  |  +0%    | ChristopherNeural | Balanced, clear, measured |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Health check & service info |
| `GET`  | `/emotions` | List all emotion profiles |
| `GET`  | `/docs` | Interactive Swagger UI |
| `POST` | `/synthesize` | **Core endpoint** — detect emotion + generate audio |
| `POST` | `/synthesize/{emotion}` | Force a specific emotion (testing) |

### POST `/synthesize`

**Request body:**
```json
{
  "text": "I'm absolutely thrilled about this incredible opportunity!"
}
```

**Response:** `audio/mpeg` binary (MP3 file)

**Response headers include:**
```
X-Detected-Emotion: joy
X-Emotion-Confidence: 0.9832
X-Voice-Rate: +22%
X-Voice-Pitch: +10Hz
X-Voice-Volume: +10%
X-Processing-Time-Ms: 1842.3
```

**Get JSON metadata instead of audio:**
```
POST /synthesize?metadata=true
```

---

## Quick Start (Local)

```bash
# 1. Clone and enter directory
cd Challenge1

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

### Example cURL requests

```bash
# Get audio file
curl -X POST "http://localhost:8000/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "I am so happy today! Everything is going wonderfully!"}' \
  --output happy_output.mp3

# Get JSON metadata (no audio download needed)
curl -X POST "http://localhost:8000/synthesize?metadata=true" \
  -H "Content-Type: application/json" \
  -d '{"text": "This is absolutely terrible. I cannot believe this happened."}'

# Force anger emotion
curl -X POST "http://localhost:8000/synthesize/anger" \
  -H "Content-Type: application/json" \
  -d '{"text": "I need this resolved immediately!"}' \
  --output angry_output.mp3
```

---

## Deploy to Render

### Using `render.yaml` (recommended)

1. Push this repository to GitHub
2. Go to [render.com](https://render.com) → **New → Blueprint**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Click **Apply** — deployment starts automatically

### Manual deploy

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect GitHub repo
3. Set:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt && python startup_preloader.py`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `TRANSFORMERS_CACHE` = `/opt/render/project/.cache/huggingface`
   - `HF_HOME` = `/opt/render/project/.cache/huggingface`

> **Note on free tier cold starts:** The model file (~67 MB) downloads on first boot.
> Use `startup_preloader.py` in the build command to cache it at build time.
> Consider upgrading to a Starter instance ($7/mo) for always-on hosting.

---

## Architecture

```
HTTP Request (text)
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI (main.py)                   │
│                                                     │
│  POST /synthesize                                   │
│       │                                             │
│       ├─── emotion_detector.py                     │
│       │    ├── DistilBERT model (HuggingFace)      │
│       │    └── Emotion → VoiceProfile mapping       │
│       │                                             │
│       └─── tts_engine.py                           │
│            ├── edge-tts (Microsoft Edge neural TTS) │
│            └── Applies rate / pitch / volume        │
│                                                     │
└─────────────────────────────────────────────────────┘
      │
      ▼
MP3 Audio Response
```

## Model Details

- **Emotion classifier:** [`bhadresh-savani/distilbert-base-uncased-emotion`](https://huggingface.co/bhadresh-savani/distilbert-base-uncased-emotion)
  - Trained on GoEmotions dataset
  - 6 output classes: joy, sadness, anger, fear, love, surprise
  - love & surprise → mapped to **joy**
- **TTS engine:** Microsoft Edge TTS (`edge-tts`) — free, no API key required
  - Uses SSML prosody parameters: `rate`, `pitch`, `volume`
  - Multiple neural voice personas per emotion

---

## File Structure

```
Challenge1/
├── main.py                # FastAPI app + all endpoints
├── emotion_detector.py    # Emotion classification + voice profile mapping
├── tts_engine.py          # edge-tts synthesis engine
├── startup_preloader.py   # Pre-downloads HF model at build time
├── requirements.txt       # Python dependencies
├── render.yaml            # Render deployment blueprint
├── .gitignore
└── README.md
```
