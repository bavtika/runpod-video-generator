import json
import re
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, SCENE_COUNT_MIN, SCENE_COUNT_MAX


def generate_storyboard(keywords: str):
    """
    Генерирует сценарий видео по ключевым словам.

    keywords: строка с ключевыми словами через запятую или пробел.
              Например: "ocean, storm, survival" или "AI future technology"
    """
    print(f"🧠 Генерируем сценарий по ключевым словам: {keywords}")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    prompt = f"""You are a world-class short-form video director specializing in viral Reels and TikToks for three niches: DATING, GAMBLING, and CRYPTO.

KEYWORDS: {keywords}

Identify which niche(s) the keywords relate to and create a compelling video script optimized for that niche:
- DATING: Use attractive people, eye contact with camera, beckoning gestures, seductive body language, boudoir/lifestyle settings. Goal: make viewers swipe right / click.
- GAMBLING: Casino atmosphere, cards, chips, roulette, confident & glamorous characters, big win moments. Goal: excitement and FOMO.
- CRYPTO: Trading setups, charts going up, confident young traders, luxury lifestyle rewards. Goal: aspiration and urgency.

You have complete creative freedom — choose angle, tone, and narrative arc that stops scrolling. Hyper-realistic photography, cinematic lighting, 8k, detailed textures, masterwork

Rules:
- Generate exactly {SCENE_COUNT_MIN} to {SCENE_COUNT_MAX} scenes
- Each scene should feel like a distinct visual moment that flows into the next
- Voiceover text must sound natural when spoken aloud — short punchy sentences, not an essay
- image_prompt: Write like a PROFESSIONAL PHOTOGRAPHER giving shoot direction. Include ALL of:
  * Shot framing: ALWAYS use "full body shot" or "three-quarter body shot" — NEVER just a portrait/headshot. LTX2 needs to see the body to animate it.
  * Camera + lens: "Leica M11 50mm f/1.4", "Sony A7III 35mm f/2.8", "Canon 5D Mark IV 85mm f/1.8"
  * ISO and natural lighting condition: "ISO 1600, mixed tungsten and LED", "ISO 400, single window daylight"
  * Real imperfections: "slight chromatic aberration", "visible pores and skin texture", "film grain", "motion blur on background"
  * Film stock or color grade: "Kodak Portra 800", "Fujifilm Eterna Cinema 800T", "Lightroom RAW edit"
  * Authentic moment: "candid", "documentary style", "unposed", "genuine expression looking at camera"
  * NEVER use: "8k", "hyperrealistic", "masterpiece", "ultra-detailed", "perfect", "flawless"
- negative_prompt: ALWAYS include "plastic skin, airbrushed, CGI, 3D render, oversmoothed, perfect symmetry, studio backdrop, artificial lighting, bad anatomy, watermark, text" plus scene-specific
- ltx2_motion: Describe PHYSICAL ACTIONS of the character's body — NOT just camera movement. The action MUST start immediately at the first frame. Use keywords like "immediately", "starts the action right away", or "instant movement". Examples:
  * DATING: "woman immediately raises hand and beckons toward camera with index finger, tilts head, smiles warmly, hair sways"
  * GAMBLING: "man instantly fans cards toward camera, raises eyebrow, leans forward on table with confident smirk"
  * CRYPTO: "man points excitedly at green chart on screen right away, turns to camera with thumbs up, leans back in chair"
  * Always end with: "starts moving immediately, smooth 24fps cinematic, natural breathing, subtle body language"
- global_style: film grade e.g. "warm golden shadows, cool midtones, slight vignette, Kodak 200 color cast"
- global_negative_prompt: universal guards against AI artifacts

OUTPUT: Respond ONLY with a valid JSON object matching this schema exactly:
{{
  "video_metadata": {{
    "title": "Short catchy title",
    "tone": "e.g. Cinematic / Inspiring / Dark / Mysterious / Energetic",
    "global_style": "Visual style descriptor applied to all scenes",
    "global_negative_prompt": "What to avoid visually across ALL scenes (e.g. blurry, deformed, ugly, text, watermark, cartoon, anime, low quality, bad anatomy)"
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "image_prompt": "Detailed visual description for image generation",
      "negative_prompt": "Scene-specific things to avoid (merge with global_negative_prompt when generating)",
      "voiceover_text": "What the narrator says in this scene. Keep it punchy.",
      "ltx2_motion": "Camera/motion direction for this scene"
    }}
  ]
}}

No markdown. No explanation. Pure JSON only."""

    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,    # Больше творческой свободы
        max_tokens=2000,
    )

    raw_text = response.choices[0].message.content

    print("\n--- СЦЕНАРИЙ ОТ ИИ ---")
    print(raw_text)
    print("----------------------\n")

    # Ищем JSON блок (иногда LLM всё равно оборачивает в ```json```)
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)

    if match:
        clean_text = match.group(0)
        try:
            result = json.loads(clean_text)
            meta = result.get("video_metadata", {})
            print(f"🎬 Название: «{meta.get('title', '?')}»")
            print(f"🎭 Тон: {meta.get('tone', '?')}")
            print(f"🖼  Стиль: {meta.get('global_style', '?')}")
            print(f"📖 Сцен: {len(result.get('scenes', []))}\n")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ ИИ выдал кривой JSON. Ошибка: {e}")
            raise
    else:
        raise ValueError("❌ ИИ не вернул JSON. Ответ был некорректным.")
