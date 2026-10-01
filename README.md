# Low-Latency Streaming Voice Agent (STT → LLM → TTS)

Full-duplex streaming voice pipeline — Whisper (STT) → LLM (OpenAI, self-hosted Ollama/vLLM optional) → Kokoro/Piper (TTS) — STT/TTS built and served from scratch, LLM swappable via adapter.

See [voice-ai-project.md](voice-ai-project.md) for motivation/CV context and [PLAN.md](PLAN.md) for the full build plan.

## Architecture

Every stage (STT/LLM/TTS/Codec) sits behind an adapter interface, swappable via the env file alone — no code changes to switch backends or move from a local Mac to a rented GPU box.

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
- [x] Agentic core — conversation memory, tool calling, agent loop, LLM fallback ([docs/agentic_module.md](docs/agentic_module.md))
- [ ] Phase 6 — Encodec integration
- [ ] Phase 7 — Eval framework (WER, latency, NISQA, throughput)

## Setup

```bash
uv sync --extra cpu   # --extra gpu on an NVIDIA box
cp .env.local.example .env.local
cp client/.env.local.example client/.env.local
# set OPENAI_API_KEY in .env.local (LLM_BACKEND=openai by default)

# to use a self-hosted LLM instead, set LLM_BACKEND=ollama or vllm in .env.local, then:
# ollama serve &
# ollama pull llama3.2   # or whichever LLM_MODEL is set in .env.local
```

## Interview coach (accounts, CVs, scoring)

```bash
uv run alembic upgrade head          # create/upgrade the database (SQLite at data/app.db by default)
uv run python -m tests.test_interview
uv run python -m tests.test_store
```

- `DATABASE_URL`: `sqlite+aiosqlite:///data/app.db` locally, `postgresql+asyncpg://...` in production. Schema changes: edit `server/store/models.py`, then `uv run alembic revision --autogenerate -m "..."` and review the file.
- Auth: Supabase Auth (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`); the client needs the same two as `NEXT_PUBLIC_*` in `client/.env.local`.
- Files: `STORAGE_BACKEND=local` (disk, `data/blobs`) or `supabase` (private bucket `STORAGE_BUCKET`, needs `SUPABASE_SERVICE_ROLE_KEY`).
- Scoring model: `SCORING_ENDPOINT` / `SCORING_MODEL` / `SCORING_API_KEY` (defaults to the conversation LLM).
- Flow: `/login` → `/new` → `/interview/<id>` → `/history`.
- Retention: run `uv run python -m server.purge` daily (cron). It permanently removes items deleted over 30 days ago and recordings older than 30 days, as the privacy policy states.
- Legal pages (`/terms`, `/privacy`, `/refunds`, `/contact`) read their facts from `client/lib/site.ts`; they are templates to have reviewed before launch.

## Run the Phase 1 check

```bash
uv run python -m tests.test_turn /path/to/sample.wav
```

Runs one full turn (transcribe → generate reply → synthesize speech) through `VoiceSession` with whichever backends `.env.local` selects, and asserts each stage produced output.

## Run the Phase 2 checks

```bash
uv run python -m tests.test_session          # state machine + barge-in, fake adapters, no models
uv run python -m tests.test_openai_audio     # OpenAI/Foundry STT+TTS adapters against a mock HTTP server
uv run python -m tests.test_resume           # dropped interview call: reconnect, takeover, hang-up, timeout — no models
uv run python -m tests.test_agent            # agent loop, tools, confirmation, fallback, concurrency — no models
uv run python -m tests.test_ws_integration   # real STT/LLM/TTS over an actual WebSocket
uv run uvicorn server.main:app --reload      # then open http://localhost:8000 in a browser
```

## Run with Docker (Phase 3)

```bash
docker compose --env-file .env.local up --build
```

Brings up `gateway`, `stt`, `tts`, `frontend` — visit `http://localhost` (Next.js client, connects directly to the gateway's `/ws` on port 8000). LLM defaults to OpenAI (needs `OPENAI_API_KEY` in `.env.local`).

To use self-hosted Ollama instead, set `LLM_BACKEND=ollama` and `LLM_ENDPOINT=http://llm:11434` in `.env.local` — the compose file still defines the `llm` (Ollama) service, it's just not started by default. Bring it up explicitly and pull a model:

```bash
docker compose --env-file .env.local up --build llm
docker compose exec llm ollama pull llama3.2
```

## Run on a rented GPU with vLLM (Phase 4)

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Same stack, but `llm` becomes `vllm/vllm-openai` with a GPU reservation instead of Ollama — no other service changes. Needs `nvidia-container-toolkit` on the host. Model is set via `VLLM_MODEL` (default `Qwen/Qwen2.5-1.5B-Instruct`, an open/ungated HF model — swap for whatever fits your GPU's memory).

## Run the Phase 5 profiling tools

```bash
# latency benchmark — real network WS against a running gateway, p50/p95 per stage
uv run python -m eval.latency_bench --host localhost --port 8000 --wav /tmp/test_sample.wav --turns 5

# GPU utilization — run in a separate terminal alongside a load test (needs nvidia-smi)
uv run python -m eval.gpu_util_log --duration 60 --out eval/results/gpu_util.csv

# torch.profiler trace of vLLM's offline Python API (kernel-level CPU+CUDA breakdown) —
# run directly on the GPU box with `uv add vllm`, not in a container, not on this Mac
uv run python -m eval.profile_llm_torch --model Qwen/Qwen2.5-1.5B-Instruct --out eval/results
```

For a system-level CUDA trace (finds which kernels dominate, not just wall time), wrap the
`vllm serve` process with NVIDIA Nsight Systems (`nsys profile -o run1 -- vllm serve ...`) —
requires the Nsight Systems CLI on the GPU box matching its CUDA/OS version; check
[NVIDIA's download page](https://developer.nvidia.com/nsight-systems) for the exact install
command for that machine rather than assuming one apt package name across versions.

Optimization order to try, cheapest first: quantization (`--quantization awq`/`fp8`) → `--max-num-seqs` tuning → `--enable-prefix-caching`. Capture `latency_bench` + `gpu_util_log` before and after each change.

## Deploy to production (one CPU-only Azure VM)

Two env profiles: `.env.local` (sqlite, Paddle sandbox, local disk storage, `tiny.en`) is read by default;
`.env.production` (Postgres, Paddle live, Azure Blob, `small.en`) is loaded by `docker-compose.prod.yml`.
`ENV_FILE=<path>` picks any other file. The client has the same pair (`client/.env.local`, `client/.env.production`);
`NEXT_PUBLIC_*` values are baked in by `next build`, so rebuild the frontend after changing them.

Large Whisper models are too slow on CPU for live calls, so production stays on `small.en` (`base.en` if
latency is still high). Kokoro has only one size (82M).

Azure resources are defined in `infra/` (Terraform): VM (`Standard_D4as_v5`, 4 vCPU / 16GB, Docker via
cloud-init), static IP, NSG (22/80/443), Postgres Flexible Server (`B_Standard_B2s`, 4GB), a storage account with a
private container, and a monthly budget alert. GitHub Actions (`.github/workflows/deploy.yml`) tests and deploys
every push to `interview-coach`: rsync to `/opt/app` on the VM, then `docker compose up -d --build`.

```bash
# once: tools, login, SSH keys (yours + a separate one for GitHub Actions)
brew install azure-cli hashicorp/tap/terraform
az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ssh-keygen -t ed25519 -f ~/.ssh/interview_vm -C "me@interview-vm"
ssh-keygen -t ed25519 -f ~/.ssh/interview_deploy -C "github-actions@interview-vm" -N ""

# provision
cp infra/terraform.tfvars.example infra/terraform.tfvars   # fill in budget_email
terraform -chdir=infra init
terraform -chdir=infra plan
terraform -chdir=infra apply
VM=$(terraform -chdir=infra output -raw vm_ip)
ssh -i ~/.ssh/interview_vm azureuser@$VM cloud-init status --wait   # Docker install finishes (~3 min)

# env files -> VM (only place they live); DATABASE_URL + storage connection string come from Terraform
cp .env.production.example .env.production                 # fill in your own secrets
cp client/.env.production.example client/.env.production   # fill in
{ cat .env.production; terraform -chdir=infra output -raw azure_env; } > .env.production.vm
scp -i ~/.ssh/interview_vm .env.production.vm azureuser@$VM:/opt/app/.env.production
scp -i ~/.ssh/interview_vm client/.env.production azureuser@$VM:/opt/app/client/.env.production
rm .env.production.vm

# GitHub Actions secrets
gh secret set VM_HOST --body "$VM"
gh secret set VM_USER --body azureuser
gh secret set VM_SSH_KEY < ~/.ssh/interview_deploy
ssh-keyscan -t ed25519 $VM | gh secret set VM_KNOWN_HOSTS

# deploy: push to interview-coach (or run the workflow by hand)
gh workflow run deploy --ref interview-coach
```

Then point the DNS A records for `interview.voicewire.tech` and `api.interview.voicewire.tech` at `$VM`; Caddy gets
TLS certificates once they resolve. Paddle live webhook: `https://api.interview.voicewire.tech/billing/webhook`.
Tear everything down: `terraform -chdir=infra destroy`.

Caddy is the only published service and load-balances (least connections) across the frontend and gateway
containers: `GATEWAY_REPLICAS=2 FRONTEND_REPLICAS=2 docker compose -f docker-compose.prod.yml up -d`. On 4 vCPUs
extra gateway replicas mostly compete with STT for CPU, so start with 1.

## Config (`.env.local` / `.env.production`)

| Var | Purpose |
|---|---|
| `STT_BACKEND` / `LLM_BACKEND` / `TTS_BACKEND` | which adapter implementation to load (`LLM_BACKEND`: `openai` / `ollama` / `vllm` — all served via one OpenAI-compatible adapter) |
| `LLM_FIRST_TOKEN_TIMEOUT` | seconds to wait for the LLM's first event before retry / failover |
| `LLM_FALLBACK_ENDPOINT` / `_MODEL` / `_API_KEY` | optional secondary LLM with circuit breaker (self-host ↔ API) |
| `STT_WORKERS` / `STT_CPU_THREADS` | parallel Whisper decodes (concurrent calls) and CPU threads per decode |
| `TTS_WORKERS` | Kokoro pipelines in the pool, one sentence each in parallel (~330MB each) |
| `MAX_SESSIONS` | concurrent calls per gateway process; extra calls are refused (client shows "all lines busy") |
| `AGENT` | default agent definition (`assistant` / `demo_tools`); per session via `?agent=` |
| `LLM_ENDPOINT` | `https://api.openai.com` by default; Ollama (`:11434`) or vLLM endpoint if self-hosting |
| `OPENAI_API_KEY` | required for `LLM_BACKEND=openai` |
| `LLM_MODEL`, `WHISPER_MODEL`, `TTS_VOICE` | model selection per stage |
| `CODEC_ENABLED` | toggle Encodec compression on the audio path |
| `DEVICE` | `cpu` / `mps` (Mac) / `cuda` (GPU box) |
| `DATABASE_URL` | `sqlite+aiosqlite:///...` locally, `postgresql+asyncpg://...?ssl=require` in production |
| `STORAGE_BACKEND` | `local` / `azure` (`AZURE_STORAGE_CONNECTION_STRING`) / `supabase` |
| `PADDLE_ENV` | `sandbox` / `production` (separate Paddle accounts, keys and price ids) |

## Stack

STT: faster-whisper · LLM: OpenAI (self-hosted Ollama/vLLM optional) · TTS: Kokoro/Piper · Codec: Encodec
Transport: FastAPI + WebSocket · Frontend: vanilla JS/Canvas · Eval: jiwer, NISQA

All models open-source/open-weight, self-hosted — no closed API calls.
