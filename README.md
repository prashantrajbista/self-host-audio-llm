# Low-Latency Streaming Voice Agent (STT → LLM → TTS)

Self-hosted, full-duplex streaming voice pipeline — Whisper (STT) → LLM (Ollama/vLLM) → Kokoro/Piper (TTS) — built and served from scratch, not just API calls.

See [voice-ai-project.md](voice-ai-project.md) for motivation/CV context and [PLAN.md](PLAN.md) for the full build plan.

## Architecture

Every stage (STT/LLM/TTS/Codec) sits behind an adapter interface, swappable via `.env` alone — no code changes to switch backends or move from a local Mac to a rented GPU box.

```
mic audio → STT adapter → LLM adapter → TTS adapter → speaker audio
             (faster-whisper)  (Ollama/vLLM)   (Kokoro/Piper)
```

## Status

- [x] Phase 0 — adapter interfaces, config, Docker stubs
- [x] Phase 1 — core pipeline working end-to-end locally (non-streaming)
- [x] Phase 2 — full-duplex streaming + interactive orb frontend (server verified end-to-end; browser mic UI untested manually)
- [ ] Phase 3 — Dockerize (per-service containers + compose)
- [ ] Phase 4 — GPU + vLLM swap
- [ ] Phase 5 — GPU profiling/optimization
- [ ] Phase 6 — Encodec integration
- [ ] Phase 7 — Eval framework (WER, latency, NISQA, throughput)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

ollama serve &
ollama pull llama3.2   # or whichever LLM_MODEL is set in .env
```

## Run the Phase 1 check

```bash
python -m tests.test_turn /path/to/sample.wav
```

Runs one full turn (transcribe → generate reply → synthesize speech) through whichever backends `.env` selects, and asserts each stage produced output.

## Run the Phase 2 checks

```bash
python -m tests.test_session          # state machine + barge-in, fake adapters, no models
python -m tests.test_ws_integration   # real STT/LLM/TTS over an actual WebSocket
uvicorn server.main:app --reload      # then open http://localhost:8000 in a browser
```

## Config (`.env`)

| Var | Purpose |
|---|---|
| `STT_BACKEND` / `LLM_BACKEND` / `TTS_BACKEND` | which adapter implementation to load |
| `LLM_ENDPOINT` | Ollama (`:11434`) locally, vLLM endpoint on the GPU box |
| `LLM_MODEL`, `WHISPER_MODEL`, `TTS_VOICE` | model selection per stage |
| `CODEC_ENABLED` | toggle Encodec compression on the audio path |
| `DEVICE` | `cpu` / `mps` (Mac) / `cuda` (GPU box) |

## Stack

STT: faster-whisper · LLM: Ollama → vLLM · TTS: Kokoro/Piper · Codec: Encodec
Transport: FastAPI + WebSocket · Frontend: vanilla JS/Canvas · Eval: jiwer, NISQA

All models open-source/open-weight, self-hosted — no closed API calls.
