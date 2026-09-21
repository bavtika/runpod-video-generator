"""
Тест LTX2 для niches: dating / gambling / crypto.
Генерирует картинку через Flux Dev → анимирует через LTX2.
Запуск: python test_ltx2.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from generation import generate_image_flux, generate_video_ltx2, download_file

os.makedirs("temp_assets", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

NEG_PHOTO = (
    "plastic skin, airbrushed, CGI, 3D render, oversmoothed, "
    "perfect symmetry, artificial lighting, watermark, text, bad anatomy, "
    "extra limbs, bad hands, disfigured"
)

TESTS = [
    # ─── DATING ───────────────────────────────────────────────────
    {
        "niche": "dating",
        "image_prompt": (
            "full body shot of a beautiful young woman in elegant lingerie, "
            "standing in a luxurious hotel room, soft warm backlight, "
            "Sony A7III 35mm f/1.8, ISO 800, "
            "inviting expression looking directly at camera, "
            "natural body proportions, slight smile, "
            "Kodak Portra 400 film emulation, candid boudoir photography"
        ),
        "motion_prompt": (
            "woman slowly raises her right hand and beckons toward camera with index finger, "
            "smiles warmly and tilts her head slightly, hair moves gently, "
            "hips shift weight to one side, natural breathing motion, "
            "smooth slow motion, 24fps cinematic"
        ),
        "label": "dating_beckon",
    }
]

for t in TESTS:
    print(f"\n{'='*55}")
    print(f"🎯 NICHE: {t['niche'].upper()}")

    print(f"🎨 Генерируем изображение Flux Dev...")
    try:
        img_url = generate_image_flux(t["image_prompt"], NEG_PHOTO)
        print(f"   ✅ {img_url[:60]}...")
    except Exception as e:
        print(f"   ❌ Flux ошибка: {e}")
        continue

    print(f"🎬 Анимируем LTX2: {t['motion_prompt'][:60]}...")
    try:
        video_url = generate_video_ltx2(img_url, t["motion_prompt"])
        out = f"outputs/test_{t['label']}.mp4"
        download_file(video_url, out)
        size_mb = os.path.getsize(out) / 1_048_576
        print(f"   ✅ Сохранено: {out} ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"   ❌ LTX2 ошибка: {e}")

print("\n✅ Готово. Открой outputs/ и проверь videos.")
