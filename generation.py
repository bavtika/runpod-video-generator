import time
import requests
import boto3
from urllib.parse import urlparse
from config import (
    RUNPOD_API_KEY, FLUX_ENDPOINT, FLUX_STEPS, FLUX_GUIDANCE,
    LTX2_ENDPOINT, VIDEO_WIDTH, VIDEO_HEIGHT, LTX2_FRAME_COUNT,
    RUNPOD_S3_ACCESS_KEY, RUNPOD_S3_SECRET_KEY, RUNPOD_S3_ENDPOINT, RUNPOD_S3_BUCKET,
    USE_CUSTOM_WORKER, RUNPOD_CUSTOM_ENDPOINT,
)

HEADERS = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}

# HTTP timeouts: (connect_timeout, read_timeout)
HTTP_TIMEOUT_SHORT  = (10, 30)    # для lightweight API-запросов (запуск задачи, статус)
HTTP_TIMEOUT_LONG   = (10, 600)   # для скачивания больших файлов

# Retry-параметры для polling
POLL_MAX_RETRIES   = 3      # кол-во сетевых ошибок подряд перед падением
POLL_BACKOFF_BASE  = 2.0    # экспоненциальный backoff (2s, 4s, 8s)


def _poll_job(url_status: str, job_id: str, poll_interval: int = 5, label: str = "") -> dict:
    """
    Polling RunPod до статуса COMPLETED / FAILED / CANCELLED.
    При сетевой ошибке — retry с exponential backoff (до POLL_MAX_RETRIES раз).

    Returns: status_res dict при COMPLETED
    Raises:  Exception при FAILED / CANCELLED / превышении retry
    """
    consecutive_errors = 0
    while True:
        time.sleep(poll_interval)
        try:
            status_res = requests.get(
                f"{url_status}/{job_id}",
                headers=HEADERS,
                timeout=HTTP_TIMEOUT_SHORT,
            ).json()
            consecutive_errors = 0  # сброс при успехе
        except requests.RequestException as e:
            consecutive_errors += 1
            wait = POLL_BACKOFF_BASE ** consecutive_errors
            print(f"   ⚠️  Сетевая ошибка при polling {label} (попытка {consecutive_errors}): {e}. Retry через {wait:.0f}с...")
            if consecutive_errors >= POLL_MAX_RETRIES:
                raise RuntimeError(f"Прервали polling {label} после {POLL_MAX_RETRIES} ошибок подряд.") from e
            time.sleep(wait)
            continue

        status = status_res.get("status")
        if status == "COMPLETED":
            return status_res
        elif status in ("FAILED", "CANCELLED"):
            raise Exception(f"Ошибка генерации {label}: {status_res}")
        else:
            print(f"   ...статус {label}: {status}")


def generate_scene_custom_worker(image_prompt: str, video_prompt: str) -> str:
    """Запускает задачу на кастомном RTX 5090 воркере и возвращает video_url."""
    print(f"🚀 Запуск кастомного RTX 5090 Воркера: {video_prompt[:50]}...")
    url_run = f"https://api.runpod.ai/v2/{RUNPOD_CUSTOM_ENDPOINT}/run"
    url_status = f"https://api.runpod.ai/v2/{RUNPOD_CUSTOM_ENDPOINT}/status"

    payload = {
        "input": {
            "image_prompt": image_prompt,
            "video_prompt": video_prompt,
            "flux_steps": FLUX_STEPS,
            "ltx_steps": 30,
            "ltx_guidance": 3.0,
        }
    }

    job = requests.post(url_run, json=payload, headers=HEADERS, timeout=HTTP_TIMEOUT_SHORT).json()
    if "id" not in job:
        raise ValueError(f"Не удалось запустить кастомный воркер: {job}")

    job_id = job["id"]
    print(f"⏳ Задача {job_id} в очереди (Custom Worker). Ждём...")

    status_res = _poll_job(url_status, job_id, poll_interval=10, label="CustomWorker")
    output = status_res.get("output", {})

    if "video_url" in output:
        return output["video_url"]
    raise KeyError(f"В ответе Custom Worker нет video_url: {output}")


def generate_image_flux(prompt: str, negative_prompt: str = "") -> str:
    """Генерирует изображение через Flux (RunPod) и возвращает URL."""
    t0 = time.time()
    print(f"🎨 Рисуем базовое изображение (Flux): {prompt[:50]}...")

    if not negative_prompt:
        negative_prompt = (
            "plastic skin, airbrushed, CGI, 3D render, oversmoothed, artificial, "
            "blurry, deformed, ugly, bad anatomy, watermark, text, logo, "
            "low quality, noisy, pixelated, disfigured, mutated"
        )

    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": -1,
            "num_inference_steps": FLUX_STEPS,
            "guidance": FLUX_GUIDANCE,
            "image_format": "png",
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
        }
    }

    # Используем /run + polling вместо /runsync:
    # runsync падает по timeout при холодном старте эндпоинта (>60с).
    # Polling надёжнее — ждём сколько нужно.
    url_run    = f"https://api.runpod.ai/v2/{FLUX_ENDPOINT}/run"
    url_status = f"https://api.runpod.ai/v2/{FLUX_ENDPOINT}/status"

    res = requests.post(url_run, json=payload, headers=HEADERS, timeout=HTTP_TIMEOUT_SHORT).json()
    if "id" not in res:
        raise ValueError(f"Ошибка Flux API (нет id): {res}")

    job_id = res["id"]
    print(f"⏳ Задача Flux {job_id} в очереди. Polling...")

    status_res = _poll_job(url_status, job_id, poll_interval=5, label="Flux")
    elapsed = time.time() - t0
    print(f"   ✅ Flux готов за {elapsed:.1f}с")
    return status_res["output"]["image_url"]


def generate_video_ltx2(image_url: str, motion_prompt: str) -> str:
    """Анимирует изображение через LTX2 (RunPod) и возвращает URL или base64-ссылку."""
    t0 = time.time()
    print(f"🎬 Анимируем видео (LTX2): {motion_prompt[:50]}...")

    url_run = f"https://api.runpod.ai/v2/{LTX2_ENDPOINT}/run"
    url_status = f"https://api.runpod.ai/v2/{LTX2_ENDPOINT}/status"

    payload = {
        "input": {
            "image": image_url,
            "prompt": motion_prompt,
            "negative_prompt": (
                "fast motion, shaky, blurry, distorted, flickering, "
                "artifacts, low quality, ugly, deformed, still image, frozen start, delayed start, static frame"
            ),
            "num_inference_steps": 50,
            "guidance_scale": 7.5,
            "frame_count": LTX2_FRAME_COUNT,  # 145 = ~6с при 24fps (кратно 8+1)
            "seed": -1,
        }
    }

    job = requests.post(url_run, json=payload, headers=HEADERS, timeout=HTTP_TIMEOUT_SHORT).json()
    if "id" not in job:
        raise ValueError(f"Не удалось запустить задачу LTX2: {job}")

    job_id = job["id"]
    print(f"⏳ Задача LTX2 {job_id} в очереди. Polling...")

    status_res = _poll_job(url_status, job_id, poll_interval=10, label="LTX2")
    elapsed = time.time() - t0
    print(f"   ✅ LTX2 готов за {elapsed:.1f}с")

    output = status_res.get("output", {})
    if "video_base64" in output:
        return f"base64:{output['video_base64']}"
    elif "video_url" in output:
        return output["video_url"]
    elif "video_filename" in output:
        filename = output["video_filename"]
        # Используем config-переменные вместо hardcoded URL
        return f"{RUNPOD_S3_ENDPOINT}/{RUNPOD_S3_BUCKET}/videos/{filename}"
    else:
        raise KeyError(f"В ответе RunPod нет URL или base64 видео: {output}")


def download_file(url: str, local_path: str) -> None:
    """Скачивает файл по URL (HTTP или S3) или декодирует из base64."""
    import base64

    if url.startswith("base64:"):
        print(f"⬇️  Сохраняем {local_path} из Base64...")
        b64_data = url[7:]
        with open(local_path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return

    print(f"⬇️  Скачиваем {local_path} из {url[:60]}...")

    parsed = urlparse(url)
    # Если это S3 RunPod URL — используем boto3 с авторизацией
    if "s3api" in parsed.netloc:
        if not RUNPOD_S3_ACCESS_KEY or not RUNPOD_S3_SECRET_KEY:
            raise ValueError(
                "❌ Для скачивания видео из RunPod S3 нужны S3 API ключи. "
                "Создайте их в консоли RunPod (Settings → S3 API Keys) и впишите в config.py "
                "(RUNPOD_S3_ACCESS_KEY и RUNPOD_S3_SECRET_KEY)."
            )

        # /bucket/path → path
        path_parts = parsed.path.lstrip("/").split("/", 1)
        object_key = path_parts[1] if len(path_parts) == 2 else parsed.path.lstrip("/")

        print(f"🔑 S3 download: endpoint={RUNPOD_S3_ENDPOINT}, bucket={RUNPOD_S3_BUCKET}, key={object_key}")
        s3 = boto3.client(
            "s3",
            endpoint_url=RUNPOD_S3_ENDPOINT,
            aws_access_key_id=RUNPOD_S3_ACCESS_KEY,
            aws_secret_access_key=RUNPOD_S3_SECRET_KEY,
            region_name="eu-ro-1",
        )
        s3.download_file(RUNPOD_S3_BUCKET, object_key, local_path)
    else:
        with requests.get(url, stream=True, headers=HEADERS, timeout=(10, 300)) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
