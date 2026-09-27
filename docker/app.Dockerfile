FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
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
