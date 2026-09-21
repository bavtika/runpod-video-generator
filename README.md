# AI Video Studio

**MLOps / DevOps portfolio project** — end-to-end pipeline that turns a keyword into a vertical short-form video using serverless GPU workers, object storage, and a containerized Streamlit control plane.

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-compose%20ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Built to demonstrate: **serverless GPU workloads**, **S3-compatible storage**, **Docker packaging**, **CI hygiene (secret scanning)**, and a **multi-stage media pipeline**.

---

## Architecture

```text
┌─────────────────────┐     HTTPS      ┌──────────────────────────────┐
│  Streamlit Studio   │───────────────▶│  OpenRouter (LLM storyboard) │
│  (Docker / local)   │                └──────────────────────────────┘
│                     │     HTTPS      ┌──────────────────────────────┐
│  main.py / CLI      │───────────────▶│  RunPod Serverless           │
│                     │                │   • Flux Dev (image)         │
│                     │◀── S3 / b64 ───│   • LTX2 worker (video)      │
└─────────┬───────────┘                └──────────────────────────────┘
          │
          ▼
   Edge TTS → MoviePy assemble → FFmpeg post-process → outputs/
```

| Layer | Responsibility | Tech |
|-------|----------------|------|
| Control plane | UI + orchestration | Streamlit, Python 3.11, Docker Compose |
| LLM | Storyboard JSON | OpenRouter (OpenAI-compatible API) |
| GPU inference | Image → short video clips | RunPod Serverless + ComfyUI handler |
| Object storage | Artifact download | RunPod S3 (`boto3`) |
| Media | TTS, montage, post-process | edge-tts, MoviePy, FFmpeg |
| CI | Lint, compile, secret scan, image build | GitHub Actions |

---

## What this shows on a CV

- **Serverless GPU**: custom RunPod worker (`runpod-worker/`) with warmup, WebSocket job wait, base64 artifact return
- **Containers**: app `Dockerfile` (ffmpeg + Streamlit healthcheck) and worker `Dockerfile`
- **Compose**: local studio stack with volume mounts for `outputs/` / `music/`
- **Secrets-as-config**: no keys in source; `.env.example` + CI secret-pattern scanner
- **Observability hooks**: stage timing report in CLI; worker progress / timeout logging
- **Idempotent workspace layout**: generated media gitignored; reproducible via env + compose

---

## Quick start

### Prerequisites

- Python 3.10+
- [Docker](https://docs.docker.com/get-docker/) (recommended) **or** local `ffmpeg`
- API accounts: [OpenRouter](https://openrouter.ai), [RunPod](https://www.runpod.io) (Geelark optional)

### Option A — Docker Compose

```bash
cp .env.example .env   # fill keys
docker compose up --build
# open http://localhost:8501
```

### Option B — Local venv

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill keys
streamlit run dashboard.py
# or: python main.py
```

---

## Configuration

All secrets and endpoints come from the environment (see `.env.example`).

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | LLM storyboard |
| `RUNPOD_API_KEY` | Flux + LTX2 / custom worker |
| `LTX2_ENDPOINT` | RunPod endpoint ID |
| `RUNPOD_S3_*` | S3 credentials for video download |
| `USE_CUSTOM_WORKER` / `RUNPOD_CUSTOM_ENDPOINT` | Route video gen to your image |
| `GEELARK_*` | Optional cloud-phone upload |

```bash
make check          # secret scan + compileall
make docker-build   # build studio image
make compose-up     # start stack
```

---

## RunPod custom worker

Package under `runpod-worker/`:

| File | Role |
|------|------|
| `handler.py` | Serverless entrypoint: load image → patch ComfyUI workflow → wait via WS → return `video_base64` |
| `workflow_api.json` | ComfyUI API-format graph (replace with your exported LTX2 workflow) |
| `Dockerfile` | Layers handler on a ComfyUI base image (`BASE_IMAGE` build-arg) |
| `requirements.txt` | `runpod`, `websocket-client`, `Pillow` |

```bash
cd runpod-worker
docker build \
  --build-arg BASE_IMAGE=runpod/worker-comfyui:5.1.0-base \
  -t ghcr.io/<you>/ai-content-ltx2-worker:latest .
# Deploy image to a RunPod Serverless endpoint, then set RUNPOD_CUSTOM_ENDPOINT
```

> Replace the placeholder `workflow_api.json` with a real **Save (API Format)** export from your ComfyUI LTX2 graph before production deploy. Node IDs in `handler.py` must match the graph.

---

## Repository layout

```text
ai-content/
├── dashboard.py / main.py     # Control plane (UI / CLI)
├── config.py                  # Env-only configuration
├── llm.py / generation.py     # LLM + RunPod clients
├── audio.py / assembly.py     # TTS + montage
├── antidetect.py              # FFmpeg post-process (hash / metadata variance)
├── uploader.py                # Optional Geelark upload
├── runpod-worker/             # Serverless GPU worker package
├── Dockerfile                 # Studio image
├── docker-compose.yml
├── .github/workflows/ci.yml
├── scripts/check_no_secrets.py
├── music/                     # Drop royalty-free MP3/WAV (gitignored)
└── outputs/                   # Generated videos (gitignored)
```

---

## CI pipeline

On every push / PR:

1. Install deps → **secret pattern scan** → Ruff critical rules → `compileall`
2. `docker build` for the studio image
3. Validate worker package (files present + handler syntax)

---

## Safety & ethics

- Do **not** commit `.env` or real API keys. Rotate any key that was ever hardcoded in a private copy.
- Post-processing (`antidetect.py`) only varies metadata / light pixel noise for content uniqueness — use responsibly and in line with platform ToS.
- Music: use royalty-free / CC0 tracks only; binary media is not published in this repo.

---

## License

MIT — see [LICENSE](LICENSE).
