# RunPod Serverless worker — ComfyUI + LTX2
# Build context: runpod-worker/
#
# Expected base: a ComfyUI image with LTX2 nodes installed, OR build your own
# from the official ComfyUI Dockerfile and copy this handler on top.
#
# Example (replace BASE with your ComfyUI+LTX2 image):
#   docker build -t ghcr.io/<you>/ai-content-ltx2-worker:latest .
#   # then deploy the image to a RunPod Serverless endpoint

ARG BASE_IMAGE=runpod/worker-comfyui:5.1.0-base
FROM ${BASE_IMAGE}

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY handler.py /app/handler.py
# Export your ComfyUI workflow as API format and place it next to the handler:
COPY workflow_api.json /app/workflow_api.json

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/handler.py"]
