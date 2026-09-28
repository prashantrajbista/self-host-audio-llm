# Low-Latency Streaming Voice Agent (STT → LLM → TTS)

Full-duplex streaming voice pipeline — Whisper (STT) → LLM (OpenAI, self-hosted Ollama/vLLM optional) → Kokoro/Piper (TTS) — STT/TTS built and served from scratch, LLM swappable via adapter.

See [voice-ai-project.md](voice-ai-project.md) for motivation/CV context and [PLAN.md](PLAN.md) for the full build plan.

## Architecture

Every stage (STT/LLM/TTS/Codec) sits behind an adapter interface, swappable via `.env` alone — no code changes to switch backends or move from a local Mac to a rented GPU box.

```
mic audio → STT adapter → LLM adapter → TTS adapter → speaker audio
             (faster-whisper)  (OpenAI/Ollama/vLLM)   (Kokoro/Piper)
```

## Status

- [x] Phase 0 — adapter interfaces, config, Docker stubs
- [x] Phase 1 — core pipeline working end-to-end locally (non-streaming)
- [x] Phase 2 — full-duplex streaming + interactive orb frontend (server verified end-to-end; browser mic UI untested manually)
- [x] Phase 3 — Dockerize (per-service containers + compose)
- [x] Phase 4 — GPU + vLLM swap (compose override written + validated; untested on real GPU hardware)
- [x] Phase 5 — GPU profiling/optimization (tooling written; `latency_bench` verified against live server, `gpu_util_log`/`profile_llm_torch` need real GPU hardware to run)
- [ ] Phase 6 — Encodec integration
- [ ] Phase 7 — Eval framework (WER, latency, NISQA, throughput)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OPENAI_API_KEY in .env (LLM_BACKEND=openai by default)

# to use a self-hosted LLM instead, set LLM_BACKEND=ollama or vllm in .env, then:
# ollama serve &
# ollama pull llama3.2   # or whichever LLM_MODEL is set in .env
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

## Run with Docker (Phase 3)

```bash
docker compose up --build
```

Brings up `gateway`, `stt`, `tts`, `frontend` — visit `http://localhost` (Next.js client, connects directly to the gateway's `/ws` on port 8000). LLM defaults to OpenAI (needs `OPENAI_API_KEY` in `.env`).

To use self-hosted Ollama instead, set `LLM_BACKEND=ollama` and `LLM_ENDPOINT=http://llm:11434` in `.env` — the compose file still defines the `llm` (Ollama) service, it's just not started by default. Bring it up explicitly and pull a model:

```bash
docker compose up --build llm
docker compose exec llm ollama pull llama3.2
```

## Run on a rented GPU with vLLM (Phase 4)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Same stack, but `llm` becomes `vllm/vllm-openai` with a GPU reservation instead of Ollama — no other service changes. Needs `nvidia-container-toolkit` on the host. Model is set via `VLLM_MODEL` (default `Qwen/Qwen2.5-1.5B-Instruct`, an open/ungated HF model — swap for whatever fits your GPU's memory).

## Run the Phase 5 profiling tools

```bash
# latency benchmark — real network WS against a running gateway, p50/p95 per stage
python -m eval.latency_bench --host localhost --port 8000 --wav /tmp/test_sample.wav --turns 5

# GPU utilization — run in a separate terminal alongside a load test (needs nvidia-smi)
python -m eval.gpu_util_log --duration 60 --out eval/results/gpu_util.csv

# torch.profiler trace of vLLM's offline Python API (kernel-level CPU+CUDA breakdown) —
# run directly on the GPU box with `pip install vllm`, not in a container, not on this Mac
python -m eval.profile_llm_torch --model Qwen/Qwen2.5-1.5B-Instruct --out eval/results
```

For a system-level CUDA trace (finds which kernels dominate, not just wall time), wrap the
`vllm serve` process with NVIDIA Nsight Systems (`nsys profile -o run1 -- vllm serve ...`) —
requires the Nsight Systems CLI on the GPU box matching its CUDA/OS version; check
[NVIDIA's download page](https://developer.nvidia.com/nsight-systems) for the exact install
command for that machine rather than assuming one apt package name across versions.

Optimization order to try, cheapest first: quantization (`--quantization awq`/`fp8`) → `--max-num-seqs` tuning → `--enable-prefix-caching`. Capture `latency_bench` + `gpu_util_log` before and after each change.

## Config (`.env`)

| Var | Purpose |
|---|---|
| `STT_BACKEND` / `LLM_BACKEND` / `TTS_BACKEND` | which adapter implementation to load (`LLM_BACKEND`: `openai` / `ollama` / `vllm`) |
| `LLM_ENDPOINT` | `https://api.openai.com` by default; Ollama (`:11434`) or vLLM endpoint if self-hosting |
| `OPENAI_API_KEY` | required for `LLM_BACKEND=openai` |
| `LLM_MODEL`, `WHISPER_MODEL`, `TTS_VOICE` | model selection per stage |
| `CODEC_ENABLED` | toggle Encodec compression on the audio path |
| `DEVICE` | `cpu` / `mps` (Mac) / `cuda` (GPU box) |

## Stack

STT: faster-whisper · LLM: OpenAI (self-hosted Ollama/vLLM optional) · TTS: Kokoro/Piper · Codec: Encodec
Transport: FastAPI + WebSocket · Frontend: vanilla JS/Canvas · Eval: jiwer, NISQA

All models open-source/open-weight, self-hosted — no closed API calls.
