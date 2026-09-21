"""
Тест полного пайплайна по концепту.
Запуск: python test_pipeline.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from config import TEMP_DIR, OUTPUT_DIR, BG_MUSIC_DIR, BG_MUSIC_VOLUME
from llm import generate_storyboard
from generation import generate_image_flux, generate_video_ltx2, download_file
from audio import generate_voiceover
from assembly import assemble_final_video

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Очищаем temp
for f in os.listdir(TEMP_DIR):
    try: os.remove(os.path.join(TEMP_DIR, f))
    except: pass

KEYWORDS = "panic, savings, ETH, ethereum, discover, invest, wait, yacht, champagne, success"

# Для быстрого теста — 2 сцены
os.environ["SCENE_COUNT_MIN"] = "2"
os.environ["SCENE_COUNT_MAX"] = "2"

print(f"🔑 Концепт: {KEYWORDS}\n")

# ── Шаг 1: Сценарий ──────────────────────────────────────────────
storyboard = generate_storyboard(KEYWORDS)
scenes     = storyboard.get("scenes", [])
meta       = storyboard.get("video_metadata", {})
global_style = meta.get("global_style", "")
global_neg   = meta.get("global_negative_prompt", "")

print(f"📖 Сцен: {len(scenes)} | Тон: {meta.get('tone')} | Стиль: {global_style[:50]}")

# ── Шаги 2-4: Flux → LTX2 → Voiceover для каждой сцены ──────────
scene_files = []
for idx, scene in enumerate(scenes):
    print(f"\n{'─'*50}")
    print(f"🎬 Сцена {idx+1}/{len(scenes)}: {scene.get('voiceover_text','')[:60]}...")

    full_prompt = f"{scene['image_prompt']}, {global_style}"
    neg = ", ".join(filter(None, [global_neg, scene.get("negative_prompt", "")]))

    # Flux
    img_url = generate_image_flux(full_prompt, neg)

    # LTX2
    video_url = generate_video_ltx2(img_url, scene["ltx2_motion"])
    video_file = os.path.join(TEMP_DIR, f"scene_{idx:02d}.mp4")
    download_file(video_url, video_file)

    # Voiceover
    audio_prefix = os.path.join(TEMP_DIR, f"audio_{idx:02d}")
    audio_file, word_timings = generate_voiceover(scene["voiceover_text"], audio_prefix)
    print(f"   🎙 Слов: {len(word_timings)}")

    scene_files.append({"video": video_file, "audio": audio_file, "word_timings": word_timings})

# ── Шаг 5: Монтаж ────────────────────────────────────────────────
ts = int(time.time())
output_path = os.path.join(OUTPUT_DIR, f"story_eth_{ts}.mp4")
print(f"\n✂️ Монтируем {len(scene_files)} сцен → {output_path}")

assemble_final_video(
    scene_files, [],
    output_path,
    crossfade_duration=0.5,
    bg_music_path=BG_MUSIC_DIR,
    bg_music_volume=BG_MUSIC_VOLUME,
)

print(f"\n✅ ГОТОВО: {output_path}")
print(f"   Открой файл и оцени результат!")
