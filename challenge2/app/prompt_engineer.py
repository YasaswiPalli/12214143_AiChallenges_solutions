"""
prompt_engineer.py
==================
Hybrid intelligent prompt engineering:
  1. PRIMARY  — Google Gemini 2.0 Flash (LLM-powered, free tier)
  2. FALLBACK — Sophisticated rule-based NLP (zero cost, works offline)

Visual consistency is enforced by injecting a "Style DNA" string into
every prompt regardless of which path generated it.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Style presets
# ---------------------------------------------------------------------------
STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "cinematic": {
        "prefix": "Award-winning cinematic photograph, photorealistic,",
        "lens": "anamorphic 35mm lens, bokeh,",
        "lighting": "dramatic golden hour lighting, volumetric light rays, cinematic color grading,",
        "quality": "8K ultra-detailed, film grain, shot on ARRI Alexa, professional color grading",
    },
    "watercolor": {
        "prefix": "Museum-quality watercolor painting, soft translucent washes, wet-on-wet technique,",
        "lens": "impressionistic composition,",
        "lighting": "gentle diffused natural light, luminous highlights,",
        "quality": "vibrant pigments, professional watercolor illustration, textured paper grain",
    },
    "flat-illustration": {
        "prefix": "Modern flat design vector illustration, bold geometric shapes,",
        "lens": "clean graphic composition, isometric perspective,",
        "lighting": "crisp solid colors, minimal drop shadows, strong visual hierarchy,",
        "quality": "SVG-quality precision, professional UI illustration, Dribbble featured",
    },
    "oil-painting": {
        "prefix": "Museum-quality oil painting in the style of the Dutch Golden Age masters,",
        "lens": "classical composition, rule of thirds,",
        "lighting": "dramatic Rembrandt chiaroscuro, rich shadows, candlelight warmth,",
        "quality": "masterful brushstrokes, thick impasto texture, gallery-worthy artwork",
    },
    "digital-art": {
        "prefix": "Stunning digital concept art, ArtStation featured, Unreal Engine render,",
        "lens": "dynamic camera angle, epic framing,",
        "lighting": "cinematic neon accent lighting, atmospheric fog, god rays,",
        "quality": "hyper-detailed, 8K resolution, photorealistic textures, trending on ArtStation",
    },
}

# ---------------------------------------------------------------------------
# Scene-position descriptors  (varied angle / framing per scene position)
# ---------------------------------------------------------------------------
POSITION_DESCRIPTORS: Dict[int, str] = {
    0: "wide establishing shot of",
    1: "intimate close-up portrait of",
    2: "medium shot depicting",
    3: "dynamic low-angle shot of",
    4: "aerial bird's-eye view of",
    5: "dramatic tracking shot of",
    6: "sweeping panoramic view of",
    7: "conclusive close-up detail of",
}

# ---------------------------------------------------------------------------
# Keyword → visual descriptor mapping
# ---------------------------------------------------------------------------
VISUAL_MAP: List[Tuple[str, str]] = [
    # Business / Corporate
    (r"\b(customer|client|buyer)\b", "a confident executive in a tailored suit shaking hands"),
    (r"\b(partner|alliance|collaboration)\b", "two professionals joining hands over a gleaming conference table"),
    (r"\b(team|workforce|employees)\b", "a diverse high-energy team collaborating in a modern glass office"),
    (r"\b(meeting|boardroom|conference)\b", "a sleek glass boardroom with city skyline views and large display screens"),
    (r"\b(ceo|executive|leader|director)\b", "a visionary leader standing before floor-to-ceiling windows overlooking a metropolis"),
    # Data / Technology
    (r"\b(data|analytics|metrics|kpi)\b", "glowing holographic data dashboards floating in a dark futuristic server room"),
    (r"\b(ai|artificial intelligence|machine learning)\b", "a luminous neural network of interconnected nodes pulsing with blue light"),
    (r"\b(cloud|platform|software|app)\b", "a sleek digital interface with floating UI elements on a transparent screen"),
    (r"\b(automation|workflow|pipeline)\b", "a choreographed sequence of glowing mechanical gears and data streams"),
    (r"\b(robot|autonomous|self-driving)\b", "a futuristic autonomous robot operating in a high-tech factory"),
    # Growth / Success
    (r"\b(growth|revenue|profit|roi)\b", "a soaring upward graph rendered as a golden mountain range at sunrise"),
    (r"\b(success|achieve|milestone|win)\b", "a triumphant athlete raising a trophy under stadium lights"),
    (r"\b(scale|expand|global|worldwide)\b", "a glowing world map with pulsing connection lines uniting every continent"),
    (r"\b(market|industry|sector)\b", "an aerial view of a bustling financial district with towering skyscrapers"),
    # Challenges / Problems
    (r"\b(problem|challenge|obstacle|barrier)\b", "a lone figure navigating a labyrinth of dark tangled wires and obstacles"),
    (r"\b(risk|threat|danger|vulnerability)\b", "storm clouds gathering over a lone lighthouse on a rocky coast"),
    (r"\b(complexity|complicated|difficult)\b", "a massive tangled web of red threads hanging in a dimly lit room"),
    # Solutions / Innovation
    (r"\b(solution|solve|resolve|fix)\b", "a brilliant lightbulb moment — golden light bursting through darkness"),
    (r"\b(innovate|innovation|breakthrough)\b", "an inventor's studio with blueprints, holographic prototypes, and sparks"),
    (r"\b(transform|revolution|disrupt|change)\b", "a chrysalis splitting open to reveal a luminescent butterfly in golden light"),
    (r"\b(launch|deploy|release|ship)\b", "a rocket igniting its engines against a star-filled night sky"),
    # Trust / Relationships
    (r"\b(trust|reliable|proven|guarantee)\b", "a solid golden bridge spanning a deep canyon in warm morning light"),
    (r"\b(secure|security|protection|shield)\b", "a glowing protective force-field encasing a digital fortress"),
    (r"\b(transparency|honest|open)\b", "a crystal-clear glass structure revealing beautiful mechanisms inside"),
    # Speed / Efficiency
    (r"\b(fast|speed|rapid|instant|real-time)\b", "blazing neon light trails streaking through a futuristic night city"),
    (r"\b(efficient|streamline|optimize|save time)\b", "gears and cogs meshing perfectly with pinpoint precision and sparks"),
    # Vision / Future
    (r"\b(future|vision|roadmap|next generation)\b", "a luminous horizon where the sky transitions from deep indigo to golden dawn"),
    (r"\b(dream|aspire|ambition)\b", "a solitary figure gazing upward at a vast star-filled galaxy"),
    (r"\b(opportunity|potential|possibility)\b", "a wide open door of golden light at the end of a dark corridor"),
    # People / Empowerment
    (r"\b(empower|enable|uplift)\b", "a hand reaching upward, breaking free from chains into a sunlit sky"),
    (r"\b(community|together|united)\b", "a powerful mosaic of diverse human silhouettes united under a sunrise"),
    (r"\b(connect|bridge|network)\b", "an intricate web of fiber-optic light connecting glowing nodes across a dark globe"),
]

# ---------------------------------------------------------------------------
# Tone detection
# ---------------------------------------------------------------------------
TONE_WORDS: Dict[str, List[str]] = {
    "triumph and achievement": [
        "success", "achieve", "win", "growth", "best", "excellent", "top", "leader", "milestone",
    ],
    "tension and rising drama": [
        "problem", "challenge", "risk", "threat", "obstacle", "struggle", "difficult", "complex",
    ],
    "urgency and momentum": [
        "fast", "quick", "now", "urgently", "immediately", "instant", "rapid", "deadline",
    ],
    "trust and reliability": [
        "trust", "reliable", "proven", "secure", "guarantee", "confidence", "stable", "safe",
    ],
    "wonder and innovation": [
        "innovate", "transform", "revolution", "disrupt", "breakthrough", "future", "vision", "ai",
    ],
    "hope and opportunity": [
        "opportunity", "potential", "dream", "aspire", "possible", "empower", "unlock", "open",
    ],
}


def detect_tone(text: str) -> str:
    text_lower = text.lower()
    for tone, keywords in TONE_WORDS.items():
        if any(kw in text_lower for kw in keywords):
            return tone
    return "professionalism and clarity"


# ---------------------------------------------------------------------------
# Visual context extractor
# ---------------------------------------------------------------------------
def extract_visual_context(text: str) -> str:
    """
    Match text against VISUAL_MAP patterns and return up to 2 descriptors.
    """
    text_lower = text.lower()
    hits: List[str] = []
    for pattern, descriptor in VISUAL_MAP:
        if re.search(pattern, text_lower):
            hits.append(descriptor)
        if len(hits) == 2:
            break
    return ", ".join(hits)


# ---------------------------------------------------------------------------
# Rule-based core (used as fallback or when Gemini is unavailable)
# ---------------------------------------------------------------------------
def _rule_based_prompt(scene: str, style: str, index: int) -> str:
    """
    Build a single rich prompt from keyword matching + style preset.
    Appends Style DNA for visual consistency across the storyboard.
    """
    from app.llm_enhancer import STYLE_DNA  # avoid circular at top-level

    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["cinematic"])
    style_dna = STYLE_DNA.get(style, "")

    position_desc = POSITION_DESCRIPTORS.get(index % len(POSITION_DESCRIPTORS), "detailed view of")
    visual_ctx = extract_visual_context(scene)
    tone = detect_tone(scene)

    if visual_ctx:
        subject_block = f"{position_desc} {visual_ctx},"
    else:
        short = re.sub(r"\s+", " ", scene[:80]).strip()
        subject_block = f"{position_desc} a high-stakes professional scene about: {short},"

    prompt_parts = [
        preset["prefix"],
        subject_block,
        preset["lens"],
        preset["lighting"],
        f"evoking a feeling of {tone},",
        preset["quality"],
        # ── Visual consistency DNA (same across all panels) ──
        style_dna + "," if style_dna else "",
        "no text, no watermark, no logo, no words",
    ]

    prompt = " ".join(p for p in prompt_parts if p)
    return re.sub(r"\s{2,}", " ", prompt).strip()


# ---------------------------------------------------------------------------
# Async hybrid orchestrator — public API
# ---------------------------------------------------------------------------
async def engineer_prompts(
    scenes: List[str],
    style: str = "cinematic",
    use_llm: bool = True,
    google_api_key: Optional[str] = None,
) -> List[str]:
    """
    Hybrid prompt engineering:
      • If `use_llm=True` and a Google API key is available, each scene is
        sent to Gemini 2.0 Flash for LLM-powered refinement.
      • Any scene where Gemini fails falls back to the rule-based engine.
      • Style DNA is appended to every prompt for visual consistency.

    This function is always async so it fits cleanly into the FastAPI
    background-task pipeline.
    """
    from app.llm_enhancer import enhance_all_prompts, get_api_key, STYLE_DNA

    key = google_api_key or get_api_key()
    use_gemini = use_llm and bool(key)

    if use_gemini:
        logger.info(f"Using Gemini 2.0 Flash for {len(scenes)} scene(s) [style={style}]")
        llm_results = await enhance_all_prompts(scenes, style, key)
    else:
        reason = "use_llm=False" if not use_llm else "no GOOGLE_API_KEY"
        logger.info(f"Using rule-based prompts ({reason}).")
        llm_results = [None] * len(scenes)

    engineered: List[str] = []
    style_dna = STYLE_DNA.get(style, "")

    for i, (scene, llm_prompt) in enumerate(zip(scenes, llm_results)):
        if llm_prompt:
            # Ensure style DNA is appended even to Gemini outputs
            if style_dna and style_dna[:30] not in llm_prompt:
                final = f"{llm_prompt} {style_dna}, no text, no watermark, no logo"
            else:
                final = llm_prompt
            source = "gemini"
        else:
            final = _rule_based_prompt(scene, style, i)
            source = "rule-based"

        final = re.sub(r"\s{2,}", " ", final).strip()
        engineered.append(final)
        logger.info(f"Scene {i + 1} [{source}]: {final[:90]}…")

    return engineered
