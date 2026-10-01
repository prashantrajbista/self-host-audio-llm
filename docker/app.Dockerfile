# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock .
# cache mount: a uv.lock change only downloads the packages that changed
# TORCH_EXTRA: cpu (default, CPU-only torch) or gpu (docker-compose.gpu-audio.yml)
ARG TORCH_EXTRA=cpu
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --extra ${TORCH_EXTRA}
ENV PATH="/app/.venv/bin:${PATH}"
# ctranslate2 (faster-whisper's backend) dlopen's libcublas/libcudnn via the linker's search
# path, not Python's — torch's pip-installed nvidia-cublas-cu12/nvidia-cudnn-cu12 wheels put
# the .so files under site-packages, invisible to the linker unless pointed at explicitly.
ENV LD_LIBRARY_PATH="/app/.venv/lib/python3.11/site-packages/nvidia/cublas/lib:/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH}"
COPY server/ server/

FROM base AS stt
EXPOSE 8001
CMD ["uvicorn", "server.services.stt_service:app", "--host", "0.0.0.0", "--port", "8001"]

FROM base AS tts
# kokoro-onnx model files (TTS_ENGINE=onnx), baked in so startup never downloads
ADD --checksum=sha256:6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx models/
ADD --checksum=sha256:bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin models/
EXPOSE 8002
CMD ["uvicorn", "server.services.tts_service:app", "--host", "0.0.0.0", "--port", "8002"]

FROM base AS gateway
COPY client/ client/
COPY packs/ packs/
COPY alembic.ini .
COPY migrations/ migrations/
EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
