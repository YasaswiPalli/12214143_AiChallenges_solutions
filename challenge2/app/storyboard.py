"""
storyboard.py
=============
Renders the final storyboard as a fully self-contained HTML page.
Images are embedded as base64 data URIs — no external file serving needed.
Uses Jinja2 templating with a dark, cinematic design.
"""

import logging
from typing import List
from jinja2 import Environment, BaseLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Jinja2 template (embedded — no file I/O = works on any Render dyno)
# ---------------------------------------------------------------------------
STORYBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} — Pitch Storyboard</title>
  <meta name="description" content="AI-generated visual storyboard: {{ title }}. {{ scene_count }} scenes, {{ style }} style.">
  <meta property="og:title" content="{{ title }}">
  <meta property="og:description" content="Visual storyboard with {{ scene_count }} scenes">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">

  <style>
    /* ── Reset & Tokens ─────────────────────────────────────── */
    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --bg0:        #07070f;
      --bg1:        #0e0e1c;
      --bg2:        #151528;
      --bg-card:    #12122080;
      --accent:     #6366f1;
      --accent2:    #8b5cf6;
      --accent-dim: rgba(99,102,241,0.15);
      --accent-glow:rgba(99,102,241,0.25);
      --border:     rgba(99,102,241,0.18);
      --border-hover:rgba(99,102,241,0.45);
      --text1:  #f1f5f9;
      --text2:  #94a3b8;
      --text3:  #4a5568;
      --gold:   #f59e0b;
      --green:  #10b981;
      --grad:   linear-gradient(135deg, var(--accent), var(--accent2));
      --r-card: 20px;
      --r-sm:   10px;
    }

    html { scroll-behavior: smooth; }

    body {
      background: var(--bg0);
      color: var(--text1);
      font-family: 'Inter', sans-serif;
      min-height: 100vh;
      overflow-x: hidden;
    }

    /* ── Ambient Background ─────────────────────────────────── */
    body::before {
      content: '';
      position: fixed; inset: 0;
      background:
        radial-gradient(ellipse 80% 60% at 15% 10%, rgba(99,102,241,.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 85%, rgba(139,92,246,.06) 0%, transparent 60%),
        radial-gradient(ellipse 40% 40% at 50% 50%, rgba(99,102,241,.03) 0%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }

    /* ── Hero ───────────────────────────────────────────────── */
    .hero {
      position: relative; z-index: 1;
      padding: 88px 24px 64px;
      text-align: center;
      border-bottom: 1px solid var(--border);
    }

    .hero-badge {
      display: inline-flex; align-items: center; gap: 8px;
      background: var(--accent-dim);
      border: 1px solid rgba(99,102,241,.35);
      border-radius: 100px;
      padding: 7px 20px;
      font-size: 12px; font-weight: 600;
      color: #a5b4fc;
      letter-spacing: 1.5px; text-transform: uppercase;
      margin-bottom: 28px;
      animation: fadeDown .6s ease both;
    }

    .hero-badge .pulse {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 8px var(--green);
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%,100% { opacity: 1; transform: scale(1); }
      50%      { opacity: .6; transform: scale(.8); }
    }

    .hero h1 {
      font-family: 'Space Grotesk', sans-serif;
      font-size: clamp(2.2rem, 6vw, 4.5rem);
      font-weight: 700;
      line-height: 1.1;
      background: linear-gradient(140deg, #f1f5f9 0%, #c7d2fe 45%, #8b5cf6 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 20px;
      animation: fadeDown .6s .1s ease both;
    }

    .hero-sub {
      font-size: 1.05rem; color: var(--text2); line-height: 1.7;
      max-width: 580px; margin: 0 auto 36px;
      animation: fadeDown .6s .2s ease both;
    }

    .hero-chips {
      display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;
      animation: fadeDown .6s .3s ease both;
    }

    .chip {
      display: inline-flex; align-items: center; gap: 6px;
      background: var(--bg2); border: 1px solid var(--border);
      border-radius: 8px; padding: 8px 16px;
      font-size: 13px; font-weight: 500; color: var(--text2);
    }
    .chip .icon { font-size: 15px; }
    .chip.accent { color: #a5b4fc; border-color: rgba(99,102,241,.35); }

    /* ── Timeline Strip ─────────────────────────────────────── */
    .timeline-strip {
      position: relative; z-index: 1;
      display: flex; justify-content: center; align-items: center;
      gap: 0; padding: 40px 24px 0;
      overflow-x: auto;
    }

    .timeline-node {
      display: flex; flex-direction: column; align-items: center; gap: 6px;
      position: relative;
    }

    .timeline-dot {
      width: 32px; height: 32px; border-radius: 50%;
      background: var(--bg2);
      border: 2px solid var(--border);
      display: flex; align-items: center; justify-content: center;
      font-size: 11px; font-weight: 700; color: var(--text3);
      transition: all .3s;
      cursor: pointer;
    }

    .timeline-dot.active {
      background: var(--grad);
      border-color: var(--accent);
      color: white;
      box-shadow: 0 0 16px var(--accent-glow);
    }

    .timeline-label {
      font-size: 10px; color: var(--text3); white-space: nowrap;
      letter-spacing: .5px; text-transform: uppercase;
    }

    .timeline-connector {
      height: 2px; width: 60px; min-width: 40px;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      opacity: .2; margin-top: -22px; flex-shrink: 0;
    }

    /* ── Main Grid ──────────────────────────────────────────── */
    .main {
      position: relative; z-index: 1;
      max-width: 1400px; margin: 0 auto;
      padding: 60px 24px 100px;
    }

    .section-eyebrow {
      text-align: center;
      font-size: 11px; letter-spacing: 3px; text-transform: uppercase;
      color: var(--text3); font-weight: 600;
      margin-bottom: 48px;
    }
    .section-eyebrow span { color: var(--accent); }

    .scenes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(420px, 100%), 1fr));
      gap: 28px;
    }

    /* ── Scene Card ─────────────────────────────────────────── */
    .scene-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--r-card);
      overflow: hidden;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      transition: transform .35s cubic-bezier(.22,.68,0,1.2),
                  box-shadow .35s ease,
                  border-color .35s ease;
      opacity: 0;
      transform: translateY(32px);
    }

    .scene-card.visible {
      opacity: 1;
      transform: translateY(0);
      transition: opacity .6s ease, transform .6s cubic-bezier(.22,.68,0,1.2),
                  box-shadow .35s ease, border-color .35s ease;
    }

    .scene-card:hover {
      transform: translateY(-10px) scale(1.01);
      box-shadow: 0 28px 70px rgba(99,102,241,.18),
                  0 0 0 1px var(--border-hover),
                  inset 0 1px 0 rgba(255,255,255,.04);
      border-color: var(--border-hover);
    }

    /* ── Image wrapper ──────────────────────────────────────── */
    .img-wrap {
      position: relative;
      width: 100%; aspect-ratio: 16/9;
      background: var(--bg1);
      overflow: hidden;
    }

    .scene-img {
      width: 100%; height: 100%;
      object-fit: cover;
      transition: transform .5s ease;
      display: block;
    }

    .scene-card:hover .scene-img { transform: scale(1.06); }

    /* ── Image Overlay ──────────────────────────────────────── */
    .img-overlay {
      position: absolute; inset: 0;
      background: linear-gradient(
        180deg,
        rgba(7,7,15,.0) 0%,
        rgba(7,7,15,.0) 50%,
        rgba(7,7,15,.55) 100%
      );
      pointer-events: none;
    }

    /* ── Number badge ───────────────────────────────────────── */
    .scene-num {
      position: absolute; top: 14px; left: 14px;
      background: rgba(0,0,0,.72);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 8px;
      padding: 5px 12px;
      font-size: 11px; font-weight: 700;
      color: var(--text2); letter-spacing: 1.5px; text-transform: uppercase;
    }
    .scene-num b { color: var(--accent); font-size: 13px; }

    /* ── Style badge ────────────────────────────────────────── */
    .style-tag {
      position: absolute; top: 14px; right: 14px;
      background: rgba(99,102,241,.82);
      backdrop-filter: blur(8px);
      border-radius: 6px; padding: 4px 10px;
      font-size: 10px; font-weight: 700; color: #fff;
      text-transform: uppercase; letter-spacing: .8px;
    }

    /* ── Card body ──────────────────────────────────────────── */
    .card-body { padding: 24px; }

    .scene-text {
      font-size: 15px; line-height: 1.75;
      color: var(--text1); font-weight: 400;
      margin-bottom: 20px;
    }

    /* ── Prompt toggle ──────────────────────────────────────── */
    .prompt-block { border-top: 1px solid var(--border); }

    .toggle-btn {
      display: flex; align-items: center; justify-content: space-between;
      width: 100%; border: none; background: none;
      padding: 14px 0 6px;
      color: var(--text3); font-size: 11px; font-weight: 700;
      letter-spacing: 1.5px; text-transform: uppercase;
      cursor: pointer; transition: color .2s;
    }
    .toggle-btn:hover { color: var(--accent); }

    .toggle-icon {
      width: 20px; height: 20px; border-radius: 50%;
      background: var(--accent-dim); border: 1px solid var(--border);
      display: flex; align-items: center; justify-content: center;
      font-size: 9px; color: var(--accent);
      transition: transform .3s ease, background .2s;
    }
    .toggle-btn.open .toggle-icon { transform: rotate(180deg); background: var(--accent); color: #fff; }

    .prompt-text {
      display: none; padding: 14px;
      background: rgba(99,102,241,.06);
      border: 1px solid rgba(99,102,241,.15);
      border-radius: var(--r-sm);
      font-size: 12px; line-height: 1.65;
      color: var(--text2); font-style: italic;
      margin-top: 4px; margin-bottom: 8px;
    }
    .prompt-text.open { display: block; }

    /* ── Footer ─────────────────────────────────────────────── */
    .footer {
      position: relative; z-index: 1;
      border-top: 1px solid var(--border);
      padding: 44px 24px;
      text-align: center;
    }

    .footer-brand {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.25rem; font-weight: 700;
      background: var(--grad);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 8px;
    }

    .footer-sub {
      font-size: 13px; color: var(--text3);
      margin-bottom: 20px;
    }

    .footer-meta {
      display: flex; justify-content: center; gap: 24px; flex-wrap: wrap;
      font-size: 12px; color: var(--text3);
    }

    .footer-meta a {
      color: inherit; text-decoration: none;
      transition: color .2s;
    }
    .footer-meta a:hover { color: var(--accent); }

    /* ── Shimmer loading state ──────────────────────────────── */
    .shimmer-box {
      background: linear-gradient(90deg, var(--bg1) 25%, var(--bg2) 50%, var(--bg1) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.8s infinite;
    }

    /* ── Animations ─────────────────────────────────────────── */
    @keyframes fadeDown {
      from { opacity: 0; transform: translateY(-16px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes shimmer {
      0%   { background-position: -200% 0; }
      100% { background-position:  200% 0; }
    }

    /* ── Print ──────────────────────────────────────────────── */
    @media print {
      body::before { display: none; }
      .scene-card { break-inside: avoid; opacity: 1 !important; transform: none !important; }
      .toggle-btn, .prompt-block { display: none; }
    }

    /* ── Responsive ─────────────────────────────────────────── */
    @media (max-width: 640px) {
      .hero { padding: 64px 16px 48px; }
      .scenes-grid { grid-template-columns: 1fr; }
      .timeline-connector { width: 32px; }
    }
  </style>
</head>
<body>

<!-- ═══ HERO ═══════════════════════════════════════════════════════════════ -->
<header class="hero" role="banner">
  <div class="hero-badge">
    <span class="pulse"></span>
    AI-Generated Storyboard
  </div>
  <h1>{{ title }}</h1>
  <p class="hero-sub">
    A {{ scene_count }}-panel visual narrative crafted from your pitch text.
    Each scene was intelligently segmented, prompt-engineered with style DNA for visual
    consistency, and rendered by FLUX.1.
  </p>
  <div class="hero-chips">
    <span class="chip"><span class="icon">🎬</span> {{ scene_count }} Scenes</span>
    <span class="chip accent"><span class="icon">✨</span> {{ style | title }} Style</span>
    <span class="chip"><span class="icon">🖼️</span> Powered by FLUX.1</span>
    <span class="chip accent"><span class="icon">🧠</span> {{ prompt_label }}</span>
    <span class="chip"><span class="icon">🆓</span> Zero Cost</span>
  </div>
</header>

<!-- ═══ TIMELINE ══════════════════════════════════════════════════════════ -->
<nav class="timeline-strip" aria-label="Scene navigation">
  {% for scene in scenes %}
    <div class="timeline-node" id="nav-{{ loop.index }}">
      <div class="timeline-dot {% if loop.index == 1 %}active{% endif %}" onclick="scrollToScene({{ loop.index }})">
        {{ loop.index }}
      </div>
      <span class="timeline-label">Scene {{ loop.index }}</span>
    </div>
    {% if not loop.last %}
      <div class="timeline-connector"></div>
    {% endif %}
  {% endfor %}
</nav>

<!-- ═══ STORYBOARD GRID ═══════════════════════════════════════════════════ -->
<main class="main" id="storyboard" role="main">
  <p class="section-eyebrow">Visual Storyboard — <span>{{ scene_count }} Scenes</span></p>

  <div class="scenes-grid" role="list">
    {% for scene, prompt, image in panels %}
    <article
      class="scene-card"
      id="scene-{{ loop.index }}"
      role="listitem"
      data-scene="{{ loop.index }}"
      aria-label="Scene {{ loop.index }} of {{ scene_count }}"
    >
      <!-- Image -->
      <div class="img-wrap">
        <img
          src="{{ image }}"
          alt="Visual representation of scene {{ loop.index }}: {{ scene[:60] }}"
          class="scene-img"
          loading="{% if loop.index <= 2 %}eager{% else %}lazy{% endif %}"
        >
        <div class="img-overlay" aria-hidden="true"></div>
        <div class="scene-num">Scene <b>{{ '%02d' | format(loop.index) }}</b></div>
        <div class="style-tag">{{ style }}</div>
      </div>

      <!-- Body -->
      <div class="card-body">
        <p class="scene-text">{{ scene }}</p>

        <!-- Engineered prompt (collapsible) -->
        <div class="prompt-block">
          <button
            class="toggle-btn"
            id="toggle-{{ loop.index }}"
            aria-expanded="false"
            aria-controls="prompt-{{ loop.index }}"
            onclick="togglePrompt({{ loop.index }})"
          >
            <span>View Engineered Prompt</span>
            <span class="toggle-icon" aria-hidden="true">▾</span>
          </button>
          <div
            class="prompt-text"
            id="prompt-{{ loop.index }}"
            role="region"
            aria-labelledby="toggle-{{ loop.index }}"
          >
            {{ prompt }}
          </div>
        </div>
      </div>
    </article>
    {% endfor %}
  </div>
</main>

<!-- ═══ FOOTER ════════════════════════════════════════════════════════════ -->
<footer class="footer" role="contentinfo">
  <div class="footer-brand">🎬 The Pitch Visualizer</div>
  <p class="footer-sub">Text → Scenes → Prompts → Images → Storyboard</p>
  <div class="footer-meta">
    <span>{{ scene_count }} scenes rendered</span>
    <span>Style: {{ style | title }}</span>
    <span>Prompts: {{ prompt_label }}</span>
    <span>Images: FLUX.1 via Pollinations.ai</span>
    <span>{{ generated_at }}</span>
  </div>
</footer>

<script>
  // ── Scroll-triggered card animations ──────────────────────────────────
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => entry.target.classList.add('visible'), i * 80);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08 }
  );
  document.querySelectorAll('.scene-card').forEach(card => observer.observe(card));

  // ── Timeline dot sync on scroll ────────────────────────────────────────
  const sceneCards = document.querySelectorAll('.scene-card');
  const timelineDots = document.querySelectorAll('.timeline-dot');

  const syncTimeline = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const idx = entry.target.dataset.scene - 1;
          timelineDots.forEach(d => d.classList.remove('active'));
          if (timelineDots[idx]) timelineDots[idx].classList.add('active');
        }
      });
    },
    { threshold: 0.5 }
  );
  sceneCards.forEach(card => syncTimeline.observe(card));

  // ── Prompt toggle ─────────────────────────────────────────────────────
  function togglePrompt(idx) {
    const btn   = document.getElementById('toggle-' + idx);
    const panel = document.getElementById('prompt-' + idx);
    const open  = panel.classList.toggle('open');
    btn.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open);
  }

  // ── Scroll to scene ───────────────────────────────────────────────────
  function scrollToScene(idx) {
    const el = document.getElementById('scene-' + idx);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------
def render_storyboard(
    scenes: List[str],
    prompts: List[str],
    images: List[str],
    style: str,
    title: str = "Pitch Storyboard",
    prompt_mode: str = "rule-based",
) -> str:
    """
    Render the storyboard HTML from scenes, prompts, and base64 images.
    Returns a self-contained HTML string.
    """
    from datetime import datetime, timezone

    env = Environment(loader=BaseLoader(), autoescape=True)
    template = env.from_string(STORYBOARD_TEMPLATE)

    panels = list(zip(scenes, prompts, images))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt_label = "🤖 Gemini 2.0 Flash" if prompt_mode == "gemini" else "⚡ Rule-Based NLP"

    html = template.render(
        title=title,
        style=style,
        scene_count=len(scenes),
        scenes=scenes,
        prompts=prompts,
        images=images,
        panels=panels,
        generated_at=generated_at,
        prompt_mode=prompt_mode,
        prompt_label=prompt_label,
    )

    logger.info(f"Storyboard HTML rendered — {len(scenes)} scenes, prompt_mode={prompt_mode}, {len(html):,} bytes.")
    return html
