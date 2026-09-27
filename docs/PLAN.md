# Voice AI Pipeline — Build Plan

## Level 1 — High-level phases
0. Setup — repo, `.env`, adapter interfaces, Docker skeleton
1. Core pipeline (local, Ollama, non-streaming)
2. Full-duplex streaming + interactive frontend (orb UI)
3. Dockerize everything (per-service containers + compose)
4. Move to rented GPU, swap LLM backend to vLLM via `.env`/compose override
5. GPU profiling/optimization (torch.profiler, nsys)
6. Encodec integration
7. Eval framework (WER, latency percentiles, NISQA, throughput)

## Level 2 — Component breakdown

**Modularity:** every stage (STT/LLM/TTS/Codec) behind an adapter interface, swappable via `.env` only. Each stage is its own service/container.

**Docker:** one Dockerfile per service (`stt`, `tts`, `gateway`, `frontend`); LLM uses official `ollama/ollama` or `vllm/vllm-openai` images (no custom build). `docker-compose.yml` (base, Mac/Ollama) + `docker-compose.gpu.yml` (override, adds vLLM + GPU reservation).

**Frontend:** ChatGPT-voice-mode/calmi.so-style interactive orb (Canvas), states: idle/listening/thinking/speaking, driven by WS events.

**Metrics per phase:**
- Phase 0: pipeline boots on Mac and GPU box via `.env` swap only, no code diff
- Phase 1: one full turn completes end-to-end, correct transcript+reply+audio
- Phase 2: per-stage latency logged; barge-in actually cuts playback
- Phase 3: same `.env`-swap-only change produces correct output containerized
- Phase 4: same pipeline correct on GPU box via `.env` swap
- Phase 5: before/after p50/p95 latency (ms) + GPU util %
- Phase 6: compression ratio + quality/WER delta
- Phase 7: WER%, latency percentiles, NISQA score, max concurrent sessions

## Level 3 — Code-level plan

### Phase 0 — Setup
- `.env.example` — STT_BACKEND, LLM_BACKEND, TTS_BACKEND, STT_ENDPOINT, LLM_ENDPOINT, TTS_ENDPOINT, CODEC_ENABLED, DEVICE
- `server/config.py` — `Settings` (pydantic-settings), `get_settings()`
- `server/adapters/stt/base.py` — `STTAdapter.transcribe_stream(audio_chunk) -> AsyncIterator[TranscriptEvent]`
- `server/adapters/llm/base.py` — `LLMAdapter.generate_stream(messages) -> AsyncIterator[str]`, `.cancel()`
- `server/adapters/tts/base.py` — `TTSAdapter.synthesize_stream(text_chunk) -> AsyncIterator[bytes]`
- `server/adapters/codec/base.py` — `CodecAdapter.encode(audio)`, `.decode(tokens)`
- `docker/{stt,tts,gateway,frontend}.Dockerfile` stubs

### Phase 1 — Core pipeline (in-process, Mac)
- `server/adapters/stt/faster_whisper_adapter.py`
- `server/adapters/llm/ollama_adapter.py`
- `server/adapters/tts/kokoro_adapter.py`
- `server/gateway/factory.py` — backend dispatch from `.env`
- `server/gateway/orchestrator.py` — `Orchestrator.run_turn(audio) -> bytes`
- `tests/test_turn.py`

### Phase 2 — Streaming + frontend
- WS envelope: `{"type": "audio_chunk|partial_transcript|token|audio_out|state|interrupt", "data": ...}`
- `server/vad/silero_vad.py`
- `server/gateway/ws_handler.py`
- `server/main.py` (FastAPI, mounts `/ws`)
- `client/app/page.tsx`, `client/components/{Orb,Transcript,ConnectButton}.tsx`
- `client/lib/{ws,audio,useVoiceSession}.ts`
- `client/public/worklet/recorder-worklet.js`

### Phase 3 — Dockerize
- `server/services/stt_service.py`, `server/services/tts_service.py` (FastAPI wrappers, own containers)
- LLM: official Ollama/vLLM images, no wrapper
- `docker/stt.Dockerfile`, `docker/tts.Dockerfile`, `docker/gateway.Dockerfile`, `docker/frontend.Dockerfile`
- `docker-compose.yml`

### Phase 4 — GPU + vLLM
- `docker-compose.gpu.yml` override — vllm/vllm-openai + GPU reservation
- `server/adapters/llm/vllm_adapter.py`

### Phase 5 — Profiling
- `eval/profile_llm.py`, `eval/gpu_util_log.py`
- nsys wrap on vllm service command (temporary compose override)
- Optimization: quantization → max-num-seqs → prefix caching, before/after diffs kept

### Phase 6 — Encodec
- `server/adapters/codec/encodec_adapter.py`
- Insert point: `ws_handler.py`, incoming audio round-trip, gated by `CODEC_ENABLED`
- `eval/codec_eval.py`

### Phase 7 — Eval framework
- `eval/wer_eval.py` (jiwer + LibriSpeech-clean)
- `eval/latency_bench.py` (p50/p95 per stage)
- `eval/nisqa_eval.py`
- `eval/throughput_test.py`
- `eval/report.py` — aggregate to markdown table

## Device split
- Mac (M2, 16GB, no CUDA): dev/logic, Ollama (Metal), frontend, Phase 0-3
- Rented GPU (Linux+CUDA): vLLM, profiling, final eval — Phase 4-7

## Stack
STT: faster-whisper · LLM: Ollama→vLLM · TTS: Kokoro/Piper · Codec: Encodec
Transport: WebSocket + FastAPI · Frontend: vanilla JS/Canvas · Orchestration: asyncio
Eval: jiwer, NISQA · All open-source/open-weight, self-hosted
