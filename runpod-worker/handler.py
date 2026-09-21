"""
RunPod Serverless Handler — ComfyUI LTX2 Video Generation
Запускается внутри контейнера Docker на RunPod.
"""
import os
import io
import json
import uuid
import time
import base64
import urllib.request
from PIL import Image
import websocket
import runpod

# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────
COMFY_API_URL    = "http://127.0.0.1:8188"
COMFY_WS_URL     = "ws://127.0.0.1:8188/ws"
COMFY_INPUT_DIR  = "/ComfyUI/input"
COMFY_OUTPUT_DIR = "/ComfyUI/output"

# Максимальное время ожидания completion от ComfyUI (секунды)
WS_MAX_WAIT_SECONDS = 600  # 10 минут

try:
    with open("workflow_api.json", "r", encoding="utf-8") as f:
        WORKFLOW_TEMPLATE = json.load(f)
except Exception as e:
    print(f"[ERROR] Failed to load workflow_api.json: {e}")
    WORKFLOW_TEMPLATE = {}


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _elapsed(t0: float) -> str:
    """Форматирует прошедшее время."""
    s = time.time() - t0
    return f"{s:.1f}s"


def get_image(image_input: str) -> Image.Image:
    """Загружает изображение из URL, data URI или base64-строки."""
    if image_input.startswith(("http://", "https://")):
        req = urllib.request.Request(image_input, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            return Image.open(io.BytesIO(response.read())).convert("RGB")
    elif image_input.startswith("data:"):
        _, encoded = image_input.split(",", 1)
        return Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
    elif len(image_input) > 200:
        # Raw base64
        return Image.open(io.BytesIO(base64.b64decode(image_input))).convert("RGB")
    else:
        return Image.open(image_input).convert("RGB")


def queue_prompt(prompt: dict, client_id: str) -> dict:
    """Отправляет задачу в очередь ComfyUI."""
    payload = json.dumps({"prompt": prompt, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_API_URL}/prompt", data=payload)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def get_history(prompt_id: str) -> dict:
    """Получает историю выполнения из ComfyUI."""
    req = urllib.request.Request(f"{COMFY_API_URL}/history/{prompt_id}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def wait_for_completion(ws: websocket.WebSocket, prompt_id: str, timeout: int = WS_MAX_WAIT_SECONDS) -> None:
    """
    Блокирующий ожидатель завершения ComfyUI через WebSocket.
    Выбрасывает:
      - RuntimeError при превышении timeout
      - Exception при execution_error из ComfyUI
    """
    deadline = time.time() + timeout
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise RuntimeError(f"⏰ Timeout: ComfyUI не завершил задачу {prompt_id} за {timeout}с")

        ws.settimeout(min(30.0, remaining))
        try:
            out = ws.recv()
        except websocket.WebSocketTimeoutException:
            # Просто нет данных — проверяем дедлайн и продолжаем
            continue

        if not isinstance(out, str):
            continue

        message = json.loads(out)
        msg_type = message.get("type")

        if msg_type == "executing":
            data = message.get("data", {})
            if data.get("node") is None and data.get("prompt_id") == prompt_id:
                return  # 🎉 Задача завершена

        elif msg_type == "execution_error":
            error_msg = message.get("data", {}).get("exception_message", "Unknown error")
            node_id   = message.get("data", {}).get("node_id", "?")
            raise Exception(f"ComfyUI ExecutionError [node {node_id}]: {error_msg}")

        elif msg_type == "progress":
            value = message.get("data", {}).get("value", "?")
            max_v = message.get("data", {}).get("max", "?")
            print(f"   🔄 ComfyUI progress: {value}/{max_v}")


def find_output_file(outputs: dict, output_prefix: str) -> str | None:
    """
    Ищет имя файла в outputs ComfyUI.
    Проверяет ключи gifs, images, videos.

    Returns: path relative to COMFY_OUTPUT_DIR, or None
    """
    for node_id, node_output in outputs.items():
        for list_name in ("gifs", "images", "videos"):
            for media in node_output.get(list_name, []):
                if media.get("filename", "").startswith(output_prefix):
                    fname = media["filename"]
                    subfolder = media.get("subfolder", "")
                    return os.path.join(subfolder, fname) if subfolder else fname
    return None


# ────────────────────────────────────────────────────────────────────
# Warmup (piins models to VRAM on cold start)
# ────────────────────────────────────────────────────────────────────

def init_warmup():
    print("🚀 [INIT] Triggering ComfyUI warmup to pin models to VRAM...")
    t0 = time.time()
    try:
        time.sleep(2)  # Ждём ComfyUI
        client_id = str(uuid.uuid4())
        prompt = json.loads(json.dumps(WORKFLOW_TEMPLATE))

        # Маленькая dummy-картинка
        dummy_img = Image.new("RGB", (128, 128), color="black")
        dummy_filename = f"warmup_{client_id}.png"
        dummy_img.save(os.path.join(COMFY_INPUT_DIR, dummy_filename))

        # Минимальные параметры для warmup
        prompt["98"]["inputs"]["image"]         = dummy_filename
        prompt["92:3"]["inputs"]["text"]         = "warmup"
        prompt["92:62"]["inputs"]["value"]       = 9     # минимум кадров
        prompt["92:11"]["inputs"]["noise_seed"]  = 1
        prompt["92:67"]["inputs"]["noise_seed"]  = 1

        ws = websocket.WebSocket()
        ws.connect(f"{COMFY_WS_URL}?clientId={client_id}")

        response  = queue_prompt(prompt, client_id)
        prompt_id = response["prompt_id"]
        wait_for_completion(ws, prompt_id, timeout=120)  # warmup — 2 мин макс
        ws.close()

        try:
            os.remove(os.path.join(COMFY_INPUT_DIR, dummy_filename))
        except OSError:
            pass

        print(f"✅ [INIT] Warmup complete in {_elapsed(t0)}")
    except Exception as e:
        print(f"⚠️  [WARN] Warmup failed (non-fatal): {e}")


init_warmup()


# ────────────────────────────────────────────────────────────────────
# Main Handler
# ────────────────────────────────────────────────────────────────────

def handler(job: dict) -> dict:
    job_input = job.get("input", {})
    job_id    = job.get("id", str(uuid.uuid4()))

    prompt_text        = job_input.get("prompt", "")
    negative_prompt    = job_input.get("negative_prompt", "blurry, low quality, jittery")
    frame_count        = job_input.get("frame_count", 145)
    seed               = job_input.get("seed", 0)
    image_url          = job_input.get("image")

    if seed <= 0:
        seed = int(time.time() * 1000) % 2**32

    print(f"\n📨 [HANDLER] Job {job_id} received")
    print(f"   prompt      : {prompt_text[:80]}")
    print(f"   frame_count : {frame_count}")
    print(f"   seed        : {seed}")

    if not image_url:
        return {"error": "Missing required 'image' parameter."}

    t_total = time.time()
    try:
        # ── 1. Загружаем и сохраняем входное изображение ────────────
        t0 = time.time()
        init_image      = get_image(image_url)
        input_filename  = f"{job_id}.png"
        input_filepath  = os.path.join(COMFY_INPUT_DIR, input_filename)
        init_image.save(input_filepath)
        print(f"   ✅ Image loaded & saved in {_elapsed(t0)}")

        # ── 2. Патчим workflow ───────────────────────────────────────
        prompt_data = json.loads(json.dumps(WORKFLOW_TEMPLATE))
        prompt_data["98"]["inputs"]["image"]        = input_filename
        prompt_data["92:3"]["inputs"]["text"]        = prompt_text
        prompt_data["92:4"]["inputs"]["text"]        = negative_prompt
        prompt_data["92:62"]["inputs"]["value"]      = frame_count
        prompt_data["92:11"]["inputs"]["noise_seed"] = seed
        prompt_data["92:67"]["inputs"]["noise_seed"] = seed + 1

        output_prefix = f"video_{job_id}"
        prompt_data["75"]["inputs"]["filename_prefix"] = output_prefix

        # ── 3. Отправляем в ComfyUI и ждём ──────────────────────────
        t0        = time.time()
        client_id = job_id
        ws        = websocket.WebSocket()
        ws.connect(f"{COMFY_WS_URL}?clientId={client_id}")

        q_response = queue_prompt(prompt_data, client_id)
        prompt_id  = q_response["prompt_id"]
        print(f"   ⏳ ComfyUI prompt_id={prompt_id}. Waiting...")

        wait_for_completion(ws, prompt_id)
        ws.close()
        print(f"   ✅ ComfyUI generation done in {_elapsed(t0)}")

        # ── 4. Ищем выходной файл ───────────────────────────────────
        history = get_history(prompt_id)
        outputs = history.get(prompt_id, {}).get("outputs", {})

        video_filename = find_output_file(outputs, output_prefix)
        if not video_filename:
            return {"error": f"Output video not found. Node outputs: {str(outputs)[:400]}"}

        # ── 5. Читаем и отдаём base64 ───────────────────────────────
        t0 = time.time()
        video_filepath = os.path.join(COMFY_OUTPUT_DIR, video_filename)
        with open(video_filepath, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")
        print(f"   ✅ Video encoded to base64 in {_elapsed(t0)} ({len(video_b64) // 1024} KB)")

        # Cleanup
        for path in (input_filepath, video_filepath):
            try:
                os.remove(path)
            except OSError:
                pass

        print(f"🏁 [HANDLER] Job {job_id} completed in {_elapsed(t_total)}")
        return {
            "status": "COMPLETED",
            "video_base64": video_b64,
            "seed": seed,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Handler Error: {str(e)}"}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
