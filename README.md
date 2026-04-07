# 12214143 AI Challenges Solutions

This repository contains my solutions for two AI challenges. Each challenge is kept in its own folder so the work can be reviewed from one GitHub submission link.

## About Me

Use this section to introduce yourself before submitting.

**Name:** Your Name  
**Roll Number / ID:** 12214143  
**Program / Department:** Your Program  
**College / University:** Your Institution  
**Email:** your.email@example.com  
**GitHub:** https://github.com/your-username  
**LinkedIn / Portfolio:** Optional link

I am a student/developer interested in building practical AI applications that combine natural language processing, web APIs, and creative user experiences. Through these challenges, I explored emotion-aware speech generation and AI-powered visual storytelling using modern Python web frameworks and open-source tools.

## Challenge 1: The Empathy Engine

Folder: [challenge1](./challenge1)

The Empathy Engine is a FastAPI-based emotion-aware text-to-speech service. It accepts text input, detects the emotional tone using a DistilBERT emotion classifier, maps the detected emotion to voice parameters such as pitch, rate, volume, and voice persona, then generates an expressive MP3 audio response using Microsoft Edge TTS.

Key ideas:

- Emotion detection from text
- Voice parameter mapping for joy, sadness, anger, fear, and neutral speech
- FastAPI endpoints for synthesis, metadata, forced-emotion testing, and health checks
- Render deployment support through `render.yaml`

## Challenge 2: The Pitch Visualizer

Folder: [challenge2](./challenge2)

The Pitch Visualizer turns narrative text into a multi-panel visual storyboard. It uses NLTK sentence segmentation, prompt engineering, optional Gemini-powered prompt refinement, and Pollinations.ai FLUX.1 image generation to create a self-contained storyboard experience.

Key ideas:

- Narrative-to-scene segmentation using NLTK
- Multiple visual styles such as cinematic, watercolor, flat illustration, oil painting, and digital art
- Async image generation with retry handling
- Storyboard HTML output and JSON storyboard data endpoints
- Render deployment support through `render.yaml`

## Repository Structure

```text
12214143_AiChallenges_solutions/
|-- README.md
|-- challenge1/
|   |-- README.md
|   |-- main.py
|   |-- emotion_detector.py
|   |-- tts_engine.py
|   |-- requirements.txt
|   `-- render.yaml
`-- challenge2/
    |-- README.md
    |-- app/
    |-- requirements.txt
    |-- run_tests.py
    |-- storyboard.html
    `-- render.yaml
```

## Running the Projects

Each challenge has its own setup instructions, dependencies, and API details in its folder-level README:

- [Challenge 1 README](./challenge1/README.md)
- [Challenge 2 README](./challenge2/README.md)

