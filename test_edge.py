import asyncio
import edge_tts

async def test():
    text = "Hello world, this is a test of edge tts."
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    
    # Сохраняем аудио и параллельно субтитры
    submaker = edge_tts.SubMaker()
    with open("test.mp3", "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                print(f"Найдено слово: {chunk}")
                submaker.feed(chunk)
                
    srt_text = submaker.get_srt()
    print("=== ИТОГОВЫЙ SRT ===")
    print(srt_text)

if __name__ == "__main__":
    asyncio.run(test())
