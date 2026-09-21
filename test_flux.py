"""
Тест генерации изображений через Flux.
Запускать: python test_flux.py

Скачивает сгенерированное изображение в temp_assets/test_flux_NNNN.png
"""
import sys, os, time, requests
sys.path.insert(0, os.path.dirname(__file__))

from generation import generate_image_flux

NEGATIVE_BASE = (
    "plastic skin, airbrushed skin, oversmoothed, CGI, 3D render, digital art, "
    "illustration, cartoon, anime, painting, rendered image, artificial lighting, "
    "perfect symmetry, flawless skin, studio backdrop, fake, synthetic, "
    "watermark, text, logo, signature, blurry, deformed, bad anatomy, "
    "disfigured, mutated, extra limbs, bad hands"
)

TESTS = [
    {
        "prompt": (
            "candid portrait of a young woman at a casino, leaning forward over "
            "roulette table, genuine smile of anticipation, "
            "Leica M11 50mm f/1.4 Summilux, ISO 1600, "
            "mixed warm tungsten and cool LED casino light, "
            "slight motion blur on spinning roulette wheel in background, "
            "shallow depth of field, visible skin texture and pores, "
            "natural makeup, Kodak Portra 800 film emulation, "
            "slight chromatic aberration, documentary photography style"
        ),
        "negative_prompt": NEGATIVE_BASE + ", posed, professional model look",
        "label": "casino_girl_v2",
    },
    {
        "prompt": (
            "physical gold Bitcoin coin lying on weathered wooden desk, "
            "Canon EF 100mm f/2.8L macro, ISO 400, f/8, "
            "single window natural daylight from left, "
            "visible metal scratches and fingerprint smudges on coin surface, "
            "dust particles visible in light beam, "
            "shallow depth of field, Lightroom RAW edit, "
            "warm afternoon light, product photography but authentic and messy"
        ),
        "negative_prompt": NEGATIVE_BASE + ", floating, space background, perfect condition",
        "label": "crypto_coin_v2",
    },
    {
        "prompt": (
            "street photography, man in his 30s checking phone showing crypto app, "
            "busy city street at night, Sony A7III 28mm f/2.8, ISO 3200, "
            "natural urban lighting: neon signs, streetlights, phone glow on face, "
            "motion blur on passing cars in background, grain visible, "
            "authentic candid moment, worn jacket, slight stubble, "
            "Fujifilm Eterna Cinema 800T color grade"
        ),
        "negative_prompt": NEGATIVE_BASE + ", posed, studio",
        "label": "crypto_street",
    },
]

os.makedirs("temp_assets", exist_ok=True)

for t in TESTS:
    print(f"\n{'='*50}")
    print(f"Тест: {t['label']}")
    print(f"Промпт: {t['prompt'][:60]}...")
    print(f"Негатив: {t['negative_prompt'][:60]}...")

    start = time.time()
    try:
        img_url = generate_image_flux(t["prompt"], t["negative_prompt"])
        elapsed = time.time() - start
        print(f"✅ URL получен за {elapsed:.1f}с: {img_url[:80]}...")

        # Скачиваем изображение
        out_path = f"temp_assets/test_flux_{t['label']}.png"
        r = requests.get(img_url, timeout=30)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        size_kb = len(r.content) // 1024
        print(f"💾 Сохранено: {out_path} ({size_kb} KB)")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

print("\n✅ Тест завершён. Открой temp_assets/ и проверь изображения.")
