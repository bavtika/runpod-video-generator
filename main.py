import os
import time
import shutil

from config import TEMP_DIR, OUTPUT_DIR, BG_MUSIC_DIR, BG_MUSIC_VOLUME
from llm import generate_storyboard
from generation import generate_image_flux, generate_video_ltx2, download_file
from audio import generate_voiceover
from assembly import assemble_final_video
from antidetect import apply_antidetect_measures
from uploader import upload_to_geelark


def _fmt(seconds: float) -> str:
    """Форматирует секунды в mm:ss."""
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def main():
    print("🚀 Старт конвейера видеогенерации...")

    pipeline_start = time.time()
    timings: dict[str, float] = {}

    # 0. Подготовка директорий + очистка temp
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for f in os.listdir(TEMP_DIR):
        try:
            os.remove(os.path.join(TEMP_DIR, f))
        except OSError:
            pass

    concept = input("\n🔑 Введите ключевые слова для видео (через запятую): ").strip()
    if not concept:
        print("❌ Ключевые слова не могут быть пустыми. Отмена.")
        return

    # Шаг 1: Сценарий
    t0 = time.time()
    try:
        storyboard = generate_storyboard(concept)
    except Exception as e:
        print(f"❌ Критическая ошибка генерации сценария: {e}")
        return
    timings["1. LLM storyboard"] = time.time() - t0

    scenes_data = storyboard.get("scenes", [])
    global_style = storyboard.get("video_metadata", {}).get("global_style", "")
    print(f"📖 Получено {len(scenes_data)} сцен из сценария.")

    scene_files = []

    try:
        # Шаги 2–3: Генерация визуала и аудио для каждой сцены
        for idx, scene in enumerate(scenes_data):
            print(f"\n--- ⏳ Обработка сцены {idx+1}/{len(scenes_data)} ---")
            scene_t0 = time.time()

            full_prompt = f"{scene['image_prompt']}, {global_style}"
            motion_prompt = scene["ltx2_motion"]
            voiceover_text = scene["voiceover_text"]

            global_neg = storyboard.get("video_metadata", {}).get("global_negative_prompt", "")
            scene_neg = scene.get("negative_prompt", "")
            negative_prompt = ", ".join(filter(None, [global_neg, scene_neg]))

            # --- ВИЗУАЛ ---
            img_url = generate_image_flux(full_prompt, negative_prompt)
            video_url = generate_video_ltx2(img_url, motion_prompt)

            video_file = os.path.join(TEMP_DIR, f"scene_{idx:02d}.mp4")
            download_file(video_url, video_file)

            # --- АУДИО И СУБТИТРЫ ---
            audio_prefix = os.path.join(TEMP_DIR, f"audio_{idx:02d}")
            audio_file, word_timings = generate_voiceover(voiceover_text, audio_prefix)

            scene_files.append({
                "video": video_file,
                "audio": audio_file,
                "word_timings": word_timings,
            })

            scene_elapsed = time.time() - scene_t0
            timings[f"  Сцена {idx+1}"] = scene_elapsed
            print(f"✅ Сцена {idx+1} готова за {_fmt(scene_elapsed)}")

        # Шаг 4: Монтаж
        t0 = time.time()
        montage_output = os.path.join(OUTPUT_DIR, "raw_montage.mp4")
        assemble_final_video(
            scene_files, [],
            montage_output,
            crossfade_duration=0.5,
            bg_music_path=BG_MUSIC_DIR,
            bg_music_volume=BG_MUSIC_VOLUME,
        )
        timings["4. Монтаж"] = time.time() - t0

        # Шаг 5: Антидетект
        t0 = time.time()
        safe_output = os.path.join(OUTPUT_DIR, "final_safe_reels.mp4")
        apply_antidetect_measures(montage_output, safe_output)
        timings["5. Антидетект"] = time.time() - t0

        # Шаг 6: Загрузка (опционально — раскомментировать для авто-постинга)
        # upload_to_geelark(safe_output)

    except Exception as e:
        print(f"\n❌ Ошибка в пайплайне: {e}")

    finally:
        # Очистка временных файлов
        print("\n🧹 Очистка временных файлов...")
        for f in os.listdir(TEMP_DIR):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except OSError:
                pass

        # ── Итоговая таблица тайминов ──────────────────────────────
        total = time.time() - pipeline_start
        print("\n" + "═" * 45)
        print("📊  TIMING REPORT")
        print("═" * 45)
        for step, elapsed in timings.items():
            print(f"  {step:<28} {_fmt(elapsed):>8}")
        print("─" * 45)
        print(f"  {'ИТОГО':<28} {_fmt(total):>8}")
        print("═" * 45)
        print("🏁 Пайплайн завершил работу.")


if __name__ == "__main__":
    main()