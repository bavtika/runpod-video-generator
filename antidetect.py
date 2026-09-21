import os
import subprocess
import random
import shutil

def apply_antidetect_measures(input_video, output_video):
    """
    Применяет FFmpeg команды для уникализации видео.
    1. Strip Metadata & Fake iPhone Metadata.
    2. Add invisible noise.
    3. Micro-cropping (0.1% - 0.5%).
    4. Brightness/Contrast variance.
    """
    # Ищем ffmpeg в PATH (решает проблему урезанного PATH в subprocess/dashboard)
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        # Пробуем типовые пути на Windows
        for candidate in [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        ]:
            if os.path.exists(candidate):
                ffmpeg_bin = candidate
                break

    if not ffmpeg_bin:
        print(f"⚠️  ffmpeg не найден! Антидетект пропущен. Копируем файл как есть.")
        import shutil as _sh
        _sh.copy2(input_video, output_video)
        return output_video

    print(f"🕵️ Начинаем уникализацию видео: {input_video} -> {output_video}")
    
    # Рандомизируем параметры для полного изменения MD5-хеша
    crop_factor = random.uniform(0.001, 0.005) # 0.1% до 0.5% кроп
    brightness = random.uniform(-0.02, 0.02)
    contrast = random.uniform(0.98, 1.02)
    noise_strength = random.randint(1, 3)
    
    now_str = "2023-10-15T12:00:00.000000Z" # Можно подставлять текущую дату
    
    # FFmpeg фильтры
    # Генерируем невидимый шум, обрезаем края, меняем настройки цвета
    # Warm color correction — нейтрализуем blue tint от LTX2
    warm = "curves=red='0/0 0.5/0.54 1/1':blue='0/0 0.5/0.47 1/0.94'"

    filters = (
        f"{warm},"
        f"crop=iw*{1-crop_factor}:ih*{1-crop_factor}:iw*{crop_factor/2}:ih*{crop_factor/2},"
        f"eq=brightness={brightness}:contrast={contrast},"
        f"noise=alls={noise_strength}:allf=t+u"
    )
    
    # Метаданные (маскируемся под iPhone 13 Pro)
    metadata = [
        "-map_metadata", "-1",                 # Удаляем все старые метаданные
        "-metadata", "creation_time=now",
        "-metadata", "make=Apple",
        "-metadata", "model=iPhone 13 Pro",
        "-metadata", "software=17.0.1",
        "-metadata", "encoder=Apple HEVC"
    ]
    
    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_video,
        "-vf", filters,
        *metadata,
        "-c:v", "libx264", 
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        output_video
    ]
    
    print(f"🚀 Запуск FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print(f"❌ Ошибка FFmpeg: {result.stderr}")
        raise Exception("FFmpeg antidetect failed")
        
    print(f"✅ Уникализация завершена! Файл {output_video} готов к загрузке.")
    return output_video
