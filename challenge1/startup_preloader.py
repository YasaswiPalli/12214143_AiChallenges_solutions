"""
startup_preloader.py
─────────────────────
Optional: pre-download the HuggingFace model before the server starts.
Run this once in the Render build phase (add to buildCommand) to avoid
cold-start delays:

    python startup_preloader.py && uvicorn main:app ...

Or add it to the Render `buildCommand`:
    pip install -r requirements.txt && python startup_preloader.py
"""

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Pre-loading emotion classification model …")
from emotion_detector import _load_pipeline
_load_pipeline()
logger.info("Model pre-loaded and cached ✓")
