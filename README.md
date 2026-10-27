# VoiceWire Interview

Open-source AI mock interviewer that works entirely by voice. It reads your CV, asks about your real experience,
follows up when an answer is vague, lets you interrupt it mid-sentence, then scores every answer.

Demo: https://youtu.be/jfJdfxSZwt4

Under the hood it is a full-duplex streaming voice pipeline (STT → LLM → TTS with barge-in) that you can run on your
own hardware: speech-to-text and text-to-speech are served locally, and the LLM is swappable between OpenAI and a
self-hosted Ollama or vLLM through the env file alone.

## Features

- **Voice interview**: real-time conversation with VAD-driven barge-in; take a moment to think, skip, or stop anytime.
- **Questions from your CV**: CV-grounded and job-post gap questions, plus a bank of behavioral and HR questions.
- **Scored report**: every answer graded against a rubric, five skill scores, delivery stats (pace, fillers, talk ratio)
  and an improved version of each answer.
- **Privacy first**: the CV is anonymized (name, contact details, profile links, IDs) before any model sees it, and
  stored replays use a disguised voice.
- **Replay and share**: replay the interview with a transcript, or share a result card showing only what you pick.
- **Interview packs**: a pack (`packs/*.toml`) is data only: persona, question bank, flow limits, rubric. Add a niche by
  adding a file.

## Architecture

```
mic audio → STT adapter → LLM adapter → TTS adapter → speaker audio
            (faster-whisper)  (OpenAI/Ollama/vLLM)   (Kokoro)
```

Every stage sits behind an adapter interface, so switching backends, or moving from a laptop to a GPU box, needs no
code changes. The server is FastAPI + WebSocket (`server/`), the web app is Next.js (`client/`), and data lives in
SQLite locally or Postgres in production.

## Quickstart

Needs Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+ and a [Supabase](https://supabase.com) project for
sign-in (the free tier is enough).

```bash
uv sync --extra cpu                     # --extra gpu on an NVIDIA box
cp .env.local.example .env.local        # set OPENAI_API_KEY and SUPABASE_*
cp client/.env.local.example client/.env.local   # set NEXT_PUBLIC_SUPABASE_*
uv run alembic upgrade head             # creates the SQLite database at data/app.db
uv run uvicorn server.main:app --reload # gateway on :8000
cd client && npm install && npm run dev # web app on :3000
```

Open http://localhost:3000, sign in, upload a CV and start an interview.

To run without any paid API, use a local LLM: set `LLM_BACKEND=ollama`, `LLM_ENDPOINT=http://localhost:11434` and
`LLM_MODEL=llama3.2` in `.env.local`, then `ollama serve` and `ollama pull llama3.2`. STT (faster-whisper) and TTS
(Kokoro) already run locally by default.

## Run with Docker

```bash
docker compose --env-file .env.local up --build
```

Brings up `gateway`, `stt`, `tts` and `frontend`; visit http://localhost. For self-hosted Ollama set
`LLM_BACKEND=ollama` and `LLM_ENDPOINT=http://llm:11434`, then:

```bash
docker compose --env-file .env.local up --build llm
docker compose exec llm ollama pull llama3.2
```

## Run on a rented GPU with vLLM

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Same stack, but `llm` becomes `vllm/vllm-openai` with a GPU reservation instead of Ollama — no other service changes. Needs `nvidia-container-toolkit` on the host. Model is set via `VLLM_MODEL` (default `Qwen/Qwen2.5-1.5B-Instruct`, an open/ungated HF model — swap for whatever fits your GPU's memory).

## Profiling (GPU)

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

## Deploy (one CPU-only Azure VM)

`infra/` holds Terraform for a small production setup: VM (`Standard_D4as_v5`, Docker via cloud-init), static IP,
NSG (22/80/443), Postgres Flexible Server, a storage account with a private container, Azure OpenAI deployments and a
monthly budget alert. Production reads `.env.production` (Postgres, Azure Blob, `small.en` Whisper) through
`docker-compose.prod.yml`; Caddy (`docker/Caddyfile`, replace `example.com` with your domain) terminates TLS and
load-balances the frontend and gateway.

```bash
brew install azure-cli hashicorp/tap/terraform && az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ssh-keygen -t ed25519 -f ~/.ssh/interview_vm

cp infra/terraform.tfvars.example infra/terraform.tfvars   # fill in budget_email
terraform -chdir=infra init && terraform -chdir=infra apply
VM=$(terraform -chdir=infra output -raw vm_ip)
ssh -i ~/.ssh/interview_vm azureuser@$VM cloud-init status --wait

cp .env.production.example .env.production                 # fill in
cp client/.env.production.example client/.env.production   # fill in
{ cat .env.production; terraform -chdir=infra output -raw azure_env; } > .env.production.vm
rsync -az --exclude '.env*' --exclude .git --exclude data/ ./ azureuser@$VM:/opt/app/
scp -i ~/.ssh/interview_vm .env.production.vm azureuser@$VM:/opt/app/.env.production
scp -i ~/.ssh/interview_vm client/.env.production azureuser@$VM:/opt/app/client/.env.production
rm .env.production.vm
ssh -i ~/.ssh/interview_vm azureuser@$VM "cd /opt/app && docker compose -f docker-compose.prod.yml up -d --build"
```

Point your domain's DNS A records at `$VM`; Caddy gets TLS certificates once they resolve. Tear everything down with
`terraform -chdir=infra destroy`.

Before going live, set `NEXT_PUBLIC_OPERATOR`, `NEXT_PUBLIC_JURISDICTION` and `NEXT_PUBLIC_SUPPORT_EMAIL` and review
the privacy and terms pages (`client/app/(site)/`): they are templates. Run `uv run python -m server.purge` daily
(cron): it removes deleted items and recordings older than 30 days, as the privacy page states.

## Monitoring

Every part is off until its values are set in `.env.production` (and `client/.env.production` for the web app), so local development needs none of it. Each piece sits on an open standard, so swapping a vendor is a config change:

| What | Tool | How it's wired | Swap by |
|---|---|---|---|
| LLM calls | Langfuse | the app's own OpenTelemetry spans (each interview, every LLM call with messages, reply, model, tokens) over OTLP to Langfuse | `LANGFUSE_*`; any OTLP tool that reads `gen_ai.*` attributes works with small changes in `server/telemetry.py` |
| Errors | Sentry | `SENTRY_DSN` (gateway), `NEXT_PUBLIC_SENTRY_DSN` in `client/.env.production` (web app) | a GlitchTip DSN (same SDK) |
| Uptime | Sentry Uptime Monitoring | set up in Sentry, no code | — |
| Notifications | Slack | `server/notify.py`: sign-ups, contact messages, gateway starts to `SLACK_WEBHOOK_URL`; failures to `SLACK_ALERTS_WEBHOOK_URL` with `@channel` | a `_send_<name>` function + `NOTIFY_BACKENDS` |
| Logs | `docker compose logs` | JSON lines (`LOG_FORMAT=json`) with the interview and user id on every line | ship stdout with any log agent |
| Traces + metrics (optional) | any OTLP backend | `OTEL_ENDPOINT` / `OTEL_HEADERS`: HTTP requests, Foundry calls, active calls, turn latency, errors, outcomes | the same two values |

LLM calls are named by what they are for (`interviewer`, `score_answer`, `cv_structure`, `jd_check`, `cv_questions`) and grouped per interview as a Langfuse session. `LANGFUSE_CAPTURE_CONTENT=false` keeps prompts and replies out (timings, tokens and cost only).

One-time setup:
1. **Slack**: create `#alerts` and `#activity`, then a Slack app with an incoming webhook for each; the URLs go in `SLACK_ALERTS_WEBHOOK_URL` / `SLACK_WEBHOOK_URL`.
2. **Langfuse**: project > Settings > API keys into `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`; `LANGFUSE_BASE_URL` is your data region's host.
3. **Sentry**: a Python project and a Next.js project; DSNs into `SENTRY_DSN` and `client/.env.production`'s `NEXT_PUBLIC_SENTRY_DSN`. Add its Slack integration (alerts to `#alerts`) and an uptime monitor on `https://api.<domain>/health`.

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

## Tests

Self-check scripts that run on fakes (no models, no network), the same set CI runs:

```bash
for t in test_store test_anonymize test_voice_anon test_interview test_agent test_markdown_strip test_session test_resume test_openai_audio test_silence test_monitoring; do
  uv run python -m tests.$t
done
uv run python -m tests.test_ws_integration   # real STT/LLM/TTS over an actual WebSocket
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
