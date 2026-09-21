import asyncio
import edge_tts


async def _generate_audio_edge(text: str, output_file: str, voice: str = "en-US-ChristopherNeural"):
    """
    Генерирует MP3-файл через edge-tts и собирает word-level тайминги.

    Returns:
        (audio_path, word_timings)
        word_timings = [{"word": "Hello", "start": 0.0, "end": 0.35}, ...]
    """
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    word_timings = []

    with open(output_file, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset и duration в единицах 100-наносекунд (ticks)
                start_sec = chunk["offset"] / 10_000_000
                duration_sec = chunk["duration"] / 10_000_000
                word_timings.append({
                    "word": chunk["text"],
                    "start": round(start_sec, 3),
                    "end": round(start_sec + duration_sec, 3),
                })

    return output_file, word_timings


def generate_voiceover(text: str, file_prefix: str = "scene") -> tuple[str, list]:
    """
    Синтезирует аудио через edge-tts (Microsoft Neural).

    Returns:
        (audio_path, word_timings)
        word_timings = [{"word": "Hello", "start": 0.0, "end": 0.35}, ...]
    """
    print(f"🎙 Синтезируем голос (Edge TTS) для: '{text[:40]}...'")
    audio_path = f"{file_prefix}.mp3"

    # asyncio.run() — корректный подход для Python 3.10+
    # Безопасно работает как в обычном скрипте, так и в subprocess из дашборда
    audio_file, word_timings = asyncio.run(_generate_audio_edge(text, audio_path))

    print(f"   ✅ Аудио готово. Слов с таймингами: {len(word_timings)}")
    return audio_file, word_timings
