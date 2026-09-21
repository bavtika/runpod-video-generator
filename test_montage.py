"""
Интеграционный тест: 2 сцены + фоновая музыка из папки music/
Запускать: python test_montage.py

Перед запуском: положи любой MP3/WAV в папку music/
Скачать треки: https://pixabay.com/music/search/ambient/
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from audio import generate_voiceover
from assembly import assemble_final_video

TEMP  = "temp_assets"
OUT   = "outputs"
MUSIC = "music"
os.makedirs(OUT, exist_ok=True)
os.makedirs(MUSIC, exist_ok=True)

scenes_text = [
    "The future of artificial intelligence is changing everything we know about creativity and technology.",
    "Every single frame of this video was crafted by machine learning models working in perfect harmony.",
]

scene_files = []
for i, text in enumerate(scenes_text):
    print(f"\n=== Сцена {i+1} ===")
    audio_file, word_timings = generate_voiceover(text, file_prefix=os.path.join(TEMP, f"test_audio_{i:02d}"))
    scene_files.append({
        "video": os.path.join(TEMP, f"scene_{i:02d}.mp4"),
        "audio": audio_file,
        "word_timings": word_timings,
    })
    print(f"   Слов: {len(word_timings)}")

output_path = os.path.join(OUT, "test_2scenes_music.mp4")

# Папка music/ — если пустая, рендерим без музыки
music_tracks = [f for f in os.listdir(MUSIC) if f.lower().endswith((".mp3", ".wav"))]
if not music_tracks:
    print(f"\n⚠️  Папка music/ пуста. Скачай треки с https://pixabay.com/music/search/ambient/")
    print("   Рендерим без музыки...")

assemble_final_video(
    scene_files, [],
    output_path,
    crossfade_duration=0.5,
    bg_music_path=MUSIC,
    bg_music_volume=0.12,
)

print(f"\n✅ ГОТОВО: {output_path}")
