import os

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # .env does not override already-set env vars
except ImportError:
    pass


def _require(name: str) -> str:
    """Return env var or empty string (callers validate at use-site)."""
    return os.getenv(name, "").strip()


# ==========================================
# Configuration — all secrets from environment
# ==========================================

# OpenRouter (LLM)
OPENROUTER_API_KEY = _require("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-70b-instruct")

# RunPod (Image & Video)
RUNPOD_API_KEY = _require("RUNPOD_API_KEY")
FLUX_ENDPOINT = os.getenv("FLUX_ENDPOINT", "black-forest-labs-flux-1-dev")
FLUX_STEPS = int(os.getenv("FLUX_STEPS", "28"))
FLUX_GUIDANCE = float(os.getenv("FLUX_GUIDANCE", "7"))

# fal.ai (optional image backend)
FAL_KEY = _require("FAL_KEY")
LTX2_ENDPOINT = _require("LTX2_ENDPOINT")

# Custom RunPod Worker (serverless GPU)
USE_CUSTOM_WORKER = os.getenv("USE_CUSTOM_WORKER", "false").lower() == "true"
RUNPOD_CUSTOM_ENDPOINT = _require("RUNPOD_CUSTOM_ENDPOINT")

# RunPod S3 (download generated videos)
RUNPOD_S3_ACCESS_KEY = _require("RUNPOD_S3_ACCESS_KEY")
RUNPOD_S3_SECRET_KEY = _require("RUNPOD_S3_SECRET_KEY")
RUNPOD_S3_ENDPOINT = os.getenv("RUNPOD_S3_ENDPOINT", "https://s3api-eu-ro-1.runpod.io")
RUNPOD_S3_BUCKET = _require("RUNPOD_S3_BUCKET")

# Geelark (optional cloud-phone upload)
GEELARK_API_KEY = _require("GEELARK_API_KEY")
GEELARK_PHONE_ID = _require("GEELARK_PHONE_ID")

# Video & generation settings
SCENE_COUNT_MIN = int(os.getenv("SCENE_COUNT_MIN", "5"))
SCENE_COUNT_MAX = int(os.getenv("SCENE_COUNT_MAX", "7"))
VIDEO_WIDTH = 768
VIDEO_HEIGHT = 1024
LTX2_FRAME_COUNT = 145  # ~6 seconds at 24fps

# Background music
BG_MUSIC_DIR = os.getenv("BG_MUSIC_DIR", "music")
BG_MUSIC_VOLUME = float(os.getenv("BG_MUSIC_VOLUME", "0.12"))

# Internal directories
TEMP_DIR = "temp_assets"
OUTPUT_DIR = "outputs"

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
