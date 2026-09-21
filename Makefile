.PHONY: help install check secrets lint compose-up compose-down docker-build worker-check

help:
	@echo "Targets:"
	@echo "  install        Create venv and install Python deps"
	@echo "  check          Secret scan + compileall"
	@echo "  secrets        Run secret hygiene scanner"
	@echo "  lint           Ruff critical checks"
	@echo "  docker-build   Build Streamlit app image"
	@echo "  compose-up     Start studio via docker compose"
	@echo "  compose-down   Stop compose stack"
	@echo "  worker-check   Validate RunPod worker package"

install:
	python -m venv .venv
	.venv/Scripts/pip install -r requirements.txt || .venv/bin/pip install -r requirements.txt

secrets:
	python scripts/check_no_secrets.py

lint:
	python -m ruff check . --select E9,F63,F7,F82 --ignore E501 || true

check: secrets
	python -m compileall -q .

docker-build:
	docker build -t ai-content-studio:local .

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

worker-check:
	test -f runpod-worker/handler.py
	test -f runpod-worker/Dockerfile
	test -f runpod-worker/workflow_api.json
	python -m py_compile runpod-worker/handler.py
