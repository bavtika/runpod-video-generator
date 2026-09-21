import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_audioclips,
)
from moviepy.audio.AudioClip import AudioClip
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.audio.fx.audio_fadeout import audio_fadeout


def pick_random_music(music_dir: str) -> str | None:
    """
    Возвращает путь к случайному MP3/WAV файлу из папки music_dir.
    Если папка пуста или не существует — возвращает None.
    """
    if not os.path.isdir(music_dir):
        return None
    tracks = [
        os.path.join(music_dir, f)
        for f in os.listdir(music_dir)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))
    ]
    if not tracks:
        return None
    chosen = random.choice(tracks)
    print(f"🎲 Рандомный трек: {os.path.basename(chosen)}")
    return chosen


# ─────────────────────────────────────────────
#  Вспомогательный модуль рендера субтитров
# ─────────────────────────────────────────────

def _find_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Ищет жирный TTF-шрифт в системе. Порядок приоритетов:
    1. Arial Bold (Windows)
    2. DejaVu Sans Bold (Linux / среды без GUI)
    3. Fallback — стандартный шрифт Pillow (без засечек).
    """
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",        # Windows Arial Bold
        "C:/Windows/Fonts/Arial_Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # Если TTF не найден — используем базовый шрифт Pillow
    return ImageFont.load_default()


def _render_subtitle_frame(
    frame: np.ndarray,
    word_timings: list,
    t: float,
    font_size: int = 58,
    y_ratio: float = 0.58,   # 58% высоты — выше центра, но ниже верха
) -> np.ndarray:
    """
    Накладывает строку субтитров на кадр видео.

    Логика:
    - Определяем, какое слово активно в момент `t`.
    - Рисуем всю строку фразы, в которой находится активное слово.
    - Активное слово — ярко-жёлтое (#FFE033), остальные — белые (#FFFFFF) со специальной обводкой.

    Возвращает изменённый numpy-кадр.
    """
    if not word_timings:
        return frame

    h, w = frame.shape[:2]

    # ── 1. Определяем активное слово и текущую «строку» (группу слов) ──
    active_idx = None
    for i, wt in enumerate(word_timings):
        if wt["start"] <= t <= wt["end"]:
            active_idx = i
            break

    if active_idx is None:
        # Если активного слова нет — ничего не рисуем
        return frame

    # ── 2. Группируем слова в строки (~5-6 слов), чтобы найти строку с активным словом ──
    WORDS_PER_LINE = 5
    line_start = (active_idx // WORDS_PER_LINE) * WORDS_PER_LINE
    line_end = min(line_start + WORDS_PER_LINE, len(word_timings))
    current_line = word_timings[line_start:line_end]

    # ── 3. Рисуем субтитры через Pillow ──
    pil_img = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_img)

    font_active = _find_font(font_size)
    font_normal = _find_font(int(font_size * 0.92))

    # Считаем общую ширину строки для центрирования
    gap = 12  # пробел между словами
    word_widths = []
    for j, wt in enumerate(current_line):
        global_j = line_start + j
        font = font_active if global_j == active_idx else font_normal
        bbox = font.getbbox(wt["word"])
        word_widths.append(bbox[2] - bbox[0])

    total_width = sum(word_widths) + gap * (len(current_line) - 1)
    x_start = (w - total_width) // 2
    y = int(h * y_ratio)

    # Рисуем слово за словом
    x = x_start
    for i, wt in enumerate(current_line):
        global_idx = line_start + i
        is_active = global_idx == active_idx

        word_text = wt["word"]
        font = font_active if is_active else font_normal
        word_w = word_widths[i]

        text_color = (255, 224, 51) if is_active else (255, 255, 255)  # Жёлтый / Белый
        shadow_color = (0, 0, 0, 200)

        # Обводка (stroke) — рисуем текст со смещением в 8 сторон
        for dx in range(-3, 4, 1):
            for dy in range(-3, 4, 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), word_text, font=font, fill=(0, 0, 0))

        # Сам текст
        draw.text((x, y), word_text, font=font, fill=text_color)

        x += word_w + gap

    return np.array(pil_img)


# ─────────────────────────────────────────────
#  Основная функция монтажа
# ─────────────────────────────────────────────

def assemble_final_video(
    scene_files: list,
    _unused_subtitles,
    output_path: str = "final_montage.mp4",
    crossfade_duration: float = 0.5,
    bg_music_path: str = None,      # путь к файлу ИЛИ папке с треками
    bg_music_volume: float = 0.12,
):
    """
    scene_files: list of dicts
        [{"video": path, "audio": path, "word_timings": [...]}]
    bg_music_path: путь к MP3/WAV файлу фоновой музыки (опционально)
    bg_music_volume: громкость подложки (0.0 – 1.0), по умолчанию 12%

    Этапы:
    1. Загрузка и обрезка клипов по длине аудио.
    2. Наложение аудио + фоновая музыка (опционально).
    3. Наложение word-level субтитров через Pillow fl_image.
    4. Сшивка клипов с crossfade через CompositeVideoClip + смещение start.
    5. Глобальный fade-in / fade-out.
    6. Рендер.
    """
    print("✂️ Начинаем монтаж с word-level субтитрами (Pillow + MoviePy)...")

    clips = []
    global_start = 0.0

    for i, scene in enumerate(scene_files):
        vid_clip  = VideoFileClip(scene["video"])
        aud_clip  = AudioFileClip(scene["audio"])
        vid_dur   = vid_clip.duration
        aud_dur   = aud_clip.duration

        # Видео играет полностью. Аудио дополняем тишиной если короче видео.
        if aud_dur < vid_dur:
            silence = AudioClip(
                make_frame=lambda t: np.zeros(2),
                duration=vid_dur - aud_dur,
                fps=44100,
            )
            aud_clip = concatenate_audioclips([aud_clip, silence])
            duration = vid_dur
        else:
            # Аудио длиннее видео — обрезаем аудио
            duration = vid_dur
            aud_clip = aud_clip.subclip(0, duration)

        vid_clip = vid_clip.set_audio(aud_clip)

        word_timings = scene.get("word_timings", [])

        # ── Наложение субтитров ──
        if word_timings:
            def make_subtitle_filter(wt):
                """Замыкание: захватываем word_timings текущей сцены."""
                def subtitle_filter(get_frame, t):
                    frame = get_frame(t)
                    return _render_subtitle_frame(frame, wt, t)
                return subtitle_filter

            vid_clip = vid_clip.fl(make_subtitle_filter(word_timings))

        # ── Crossfade ──
        if i == 0:
            vid_clip = vid_clip.set_start(0)
        else:
            vid_clip = vid_clip.set_start(global_start).crossfadein(crossfade_duration)

        clips.append(vid_clip)

        # Следующий клип начинается чуть раньше конца текущего (crossfade overlap)
        global_start += duration - crossfade_duration

    # ── Сборка финальной композиции ──
    final = CompositeVideoClip(clips)
    final = final.fadein(0.8).fadeout(0.8)

    total_duration = final.duration
    print(f"🎬 Итоговая длина видео: {total_duration:.1f}с.")

    # ── Фоновая музыка ──
    if bg_music_path:
        # Если передана папка — выбираем рандомный трек
        if os.path.isdir(bg_music_path):
            bg_music_path = pick_random_music(bg_music_path)

        if bg_music_path and os.path.exists(bg_music_path):
            print(f"🎵 Добавляем фоновую музыку: {os.path.basename(bg_music_path)} (громкость {int(bg_music_volume*100)}%)")
            music = AudioFileClip(bg_music_path)

            # Зацикливаем, если трек короче видео
            if music.duration < total_duration:
                music = audio_loop(music, duration=total_duration)
            else:
                music = music.subclip(0, total_duration)

            # Плавное появление/затухание музыки
            music = audio_fadein(music, 2.0)
            music = audio_fadeout(music, 2.0)
            music = music.volumex(bg_music_volume)

            # Микшируем voiceover + музыка
            main_audio = final.audio
            mixed_audio = CompositeAudioClip([main_audio, music])
            final = final.set_audio(mixed_audio)
        else:
            print(f"⚠️  Файл музыки не найден: {bg_music_path}. Пропускаем.")

    print("🚀 Начинаем рендер...")

    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
    )

    final.close()
    for c in clips:
        c.close()

    print(f"🎉 Монтаж завершён! Файл: {output_path}")
    return output_path
