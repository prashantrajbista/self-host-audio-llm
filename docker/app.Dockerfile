FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ctranslate2 (faster-whisper's backend) dlopen's libcublas/libcudnn via the linker's search
# path, not Python's — torch's pip-installed nvidia-cublas-cu12/nvidia-cudnn-cu12 wheels put
# the .so files under site-packages, invisible to the linker unless pointed at explicitly.
ENV LD_LIBRARY_PATH="/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH}"
COPY server/ server/

FROM base AS stt
EXPOSE 8001
CMD ["uvicorn", "server.services.stt_service:app", "--host", "0.0.0.0", "--port", "8001"]

FROM base AS tts
EXPOSE 8002
CMD ["uvicorn", "server.services.tts_service:app", "--host", "0.0.0.0", "--port", "8002"]

FROM base AS gateway
COPY client/ client/
EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
