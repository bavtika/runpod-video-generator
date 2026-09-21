import os
import requests
from config import GEELARK_API_KEY, GEELARK_PHONE_ID

GEELARK_BASE_URL = "https://api.geelark.com/v1"

def upload_to_geelark(video_path):
    """
    Загружает видео в файловую систему облачного телефона Geelark (в папку Downloads).
    """
    print(f"☁️ Начинаем загрузку файла {video_path} в Geelark (Phone ID: {GEELARK_PHONE_ID})...")
    
    if not GEELARK_API_KEY or GEELARK_API_KEY == "YOUR_GEELARK_API_KEY":
        print("⚠️ ВНИМАНИЕ: Не задан GEELARK_API_KEY. Пропуск загрузки.")
        return False
        
    filename = os.path.basename(video_path)
    
    # 1. Сначала нужно загрузить файл в временное хранилище Geelark
    upload_url = f"{GEELARK_BASE_URL}/phone/file/upload"
    headers = {
        "Authorization": f"Bearer {GEELARK_API_KEY}"
    }
    
    print("📤 Шаг 1: Загрузка на временный сервер Geelark...")
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (filename, f, 'video/mp4')}
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status()
            
        data = response.json()
        if data.get('code') != 0:
            raise Exception(f"Ошибка загрузки файла в Geelark: {data.get('msg')}")
            
        temp_file_url = data['data']['url']
        print(f"✅ Временный URL получен: {temp_file_url}")
        
    except Exception as e:
        print(f"❌ Ошибка на Шаге 1 (загрузка во временное хранилище): {e}")
        return False
        
    # 2. Теперь отправляем команду телефону скачать этот файл в себя
    print(f"📱 Шаг 2: Отправка файла в телефон {GEELARK_PHONE_ID}...")
    push_url = f"{GEELARK_BASE_URL}/phone/{GEELARK_PHONE_ID}/file/push"
    
    payload = {
        "url": temp_file_url,
        "filename": filename,
        "path": "/storage/emulated/0/Download" # Папка загрузок Android
    }
    
    try:
        response = requests.post(push_url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') != 0:
            raise Exception(f"Ошибка пуша файла в телефон Geelark: {data.get('msg')}")
            
        print(f"🎉 Ресурс успешно размещен в телефоне! Видео доступно в галерее или папке загрузок.")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка на Шаге 2 (отправка в телефон): {e}")
        return False
