# VoiceWire Interview

Open-source AI mock interviewer that works entirely by voice. It reads your CV, asks about your real experience,
follows up when an answer is vague, lets you interrupt it mid-sentence, then scores every answer.

**Contents:** [Demo](#demo) · [Features](#features) · [How it works](#how-it-works) · [Setup](#setup) ·
[Deployment](#deployment) · [Configuration](#configuration) · [Monitoring](#monitoring) ·
[Profiling](#profiling-gpu) · [Tests](#tests) · [Roadmap](#roadmap) · [Troubleshooting](#troubleshooting) ·
[Contributing](#contributing) · [Security](#security) · [Acknowledgements](#acknowledgements) · [License](#license)

## Demo

https://youtu.be/jfJdfxSZwt4

## Features

### Interview

- **Voice conversation**: real-time, with VAD-driven barge-in; take a moment to think, skip, or stop anytime.
- **Questions from your CV**: CV-grounded and job-post gap questions, plus a bank of behavioral and HR questions.
- **Interview packs**: a pack (`packs/*.toml`) is data only: persona, question bank, flow limits, rubric. Add a niche by
  adding a file.

### Feedback

- **Scored report**: every answer graded against a rubric, five skill scores, and an improved version of each answer.
- **Delivery stats**: speaking pace, filler words, talk ratio and answer length.
- **Replay and share**: replay the interview with a transcript, or share a result card showing only what you pick.

### Privacy

- **Anonymized CV**: name, contact details, profile links and IDs are removed before any model sees it.
- **Disguised replays**: stored recordings use a pitch- and formant-shifted voice.
- **Retention**: deleted items and recordings older than 30 days are purged.

## How it works

### Pipeline

```
mic audio → STT adapter → LLM adapter → TTS adapter → speaker audio
            (faster-whisper)  (OpenAI/Ollama/vLLM)   (Kokoro)
```

A full-duplex streaming voice pipeline. Every stage sits behind an adapter interface, so switching backends, or moving
from a laptop to a GPU box, needs only env changes. STT and TTS are served locally; the LLM can be OpenAI or a
self-hosted Ollama or vLLM.

### Project layout

| Path | What |
|---|---|
| `server/` | FastAPI + WebSocket gateway: voice session, adapters, interview agent, scoring, storage |
| `client/` | Next.js web app |
| `packs/` | interview packs (questions, rubric, persona) |
| `migrations/` | Alembic database migrations |
| `infra/` | Terraform for an Azure deployment |
| `docker/`, `docker-compose*.yml` | containers and compose files |
| `eval/` | latency and GPU profiling tools |
| `tests/` | self-check scripts |

## Setup

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node 20+
- A [Supabase](https://supabase.com) project for sign-in (the free tier is enough)
- An OpenAI API key, or a local LLM (see [Use a local LLM](#use-a-local-llm))

### 1. Install dependencies

```bash
uv sync --extra cpu                      # --extra gpu on an NVIDIA box
cd client && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.local.example .env.local                 # set OPENAI_API_KEY and SUPABASE_*
cp client/.env.local.example client/.env.local   # set NEXT_PUBLIC_SUPABASE_*
```

### 3. Create the database

```bash
uv run alembic upgrade head              # SQLite at data/app.db
```

### 4. Start the app

```bash
uv run uvicorn server.main:app --reload  # gateway on :8000
cd client && npm run dev                 # web app on :3000
```

Open http://localhost:3000, sign in, upload a CV and start an interview.

### Use a local LLM

To run without any paid API, set these in `.env.local`:

```bash
LLM_BACKEND=ollama
LLM_ENDPOINT=http://localhost:11434
LLM_MODEL=llama3.2
```

Then `ollama serve` and `ollama pull llama3.2`. STT (faster-whisper) and TTS (Kokoro) already run locally by default.

### Run with Docker

```bash
docker compose --env-file .env.local up --build
```

Brings up `gateway`, `stt`, `tts` and `frontend`; visit http://localhost. For Ollama in Docker set
`LLM_BACKEND=ollama` and `LLM_ENDPOINT=http://llm:11434`, then:

```bash
docker compose --env-file .env.local up --build llm
docker compose exec llm ollama pull llama3.2
```

### Run on a GPU with vLLM

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Same stack, but `llm` becomes `vllm/vllm-openai` with a GPU reservation instead of Ollama. Needs
`nvidia-container-toolkit` on the host. Set the model with `VLLM_MODEL` (default `Qwen/Qwen2.5-1.5B-Instruct`, an
ungated Hugging Face model; pick one that fits your GPU's memory).

## Deployment

`infra/` holds Terraform for one CPU-only Azure VM: VM (`Standard_D4as_v5`, Docker via cloud-init), static IP, NSG
(22/80/443), Postgres Flexible Server, a storage account with a private container, Azure OpenAI deployments and a
monthly budget alert. Production reads `.env.production` (Postgres, Azure Blob, `small.en` Whisper) through
`docker-compose.prod.yml`; Caddy terminates TLS and load-balances the frontend and gateway.

### 1. Provision infrastructure

```bash
brew install azure-cli hashicorp/tap/terraform && az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ssh-keygen -t ed25519 -f ~/.ssh/interview_vm

cp infra/terraform.tfvars.example infra/terraform.tfvars   # fill in budget_email
terraform -chdir=infra init && terraform -chdir=infra apply
VM=$(terraform -chdir=infra output -raw vm_ip)
ssh -i ~/.ssh/interview_vm azureuser@$VM cloud-init status --wait
```

### 2. Configure environment

```bash
cp .env.production.example .env.production                 # fill in
cp client/.env.production.example client/.env.production   # fill in
{ cat .env.production; terraform -chdir=infra output -raw azure_env; } > .env.production.vm
```

### 3. Ship the app

```bash
rsync -az --exclude '.env*' --exclude .git --exclude data/ ./ azureuser@$VM:/opt/app/
scp -i ~/.ssh/interview_vm .env.production.vm azureuser@$VM:/opt/app/.env.production
scp -i ~/.ssh/interview_vm client/.env.production azureuser@$VM:/opt/app/client/.env.production
rm .env.production.vm
ssh -i ~/.ssh/interview_vm azureuser@$VM "cd /opt/app && docker compose -f docker-compose.prod.yml up -d --build"
```

### 4. Domain and TLS

Replace `example.com` in `docker/Caddyfile` with your domain and point its DNS A records at `$VM`; Caddy gets TLS
certificates once they resolve.

### 5. Before going live

- Set `NEXT_PUBLIC_OPERATOR`, `NEXT_PUBLIC_JURISDICTION` and `NEXT_PUBLIC_SUPPORT_EMAIL`, and review the privacy and
  terms pages (`client/app/(site)/`): they are templates.
- Run `uv run python -m server.purge` daily (cron): it removes deleted items and recordings older than 30 days, as the
  privacy page states.

### Tear down

```bash
terraform -chdir=infra destroy
```

## Configuration

Set in `.env.local` (development) or `.env.production`.

### Speech pipeline

| Var | Purpose |
|---|---|
| `STT_BACKEND` / `LLM_BACKEND` / `TTS_BACKEND` | which adapter to load (`LLM_BACKEND`: `openai` / `ollama` / `vllm`, all served by one OpenAI-compatible adapter) |
| `LLM_MODEL`, `WHISPER_MODEL`, `TTS_VOICE` | model per stage |
| `CODEC_ENABLED` | toggle Encodec compression on the audio path |
| `DEVICE` | `cpu` / `mps` (Mac) / `cuda` (GPU box) |

### LLM

| Var | Purpose |
|---|---|
| `LLM_ENDPOINT` | `https://api.openai.com` by default; Ollama (`:11434`) or vLLM endpoint if self-hosting |
| `OPENAI_API_KEY` | required for `LLM_BACKEND=openai` |
| `LLM_FIRST_TOKEN_TIMEOUT` | seconds to wait for the LLM's first event before retry / failover |
| `LLM_FALLBACK_ENDPOINT` / `_MODEL` / `_API_KEY` | optional secondary LLM with circuit breaker (self-host ↔ API) |
| `SCORING_ENDPOINT` / `_MODEL` / `_API_KEY` | model that grades answers; empty reuses the conversation LLM |
| `AGENT` | default agent definition (`assistant` / `demo_tools`); per session via `?agent=` |

### Capacity

| Var | Purpose |
|---|---|
| `STT_WORKERS` / `STT_CPU_THREADS` | parallel Whisper decodes (concurrent calls) and CPU threads per decode |
| `TTS_WORKERS` | Kokoro pipelines in the pool, one sentence each in parallel (~330MB each) |
| `MAX_SESSIONS` | concurrent calls per gateway process; extra calls are refused (client shows "all lines busy") |

### Data and auth

| Var | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///...` locally, `postgresql+asyncpg://...?ssl=require` in production |
| `STORAGE_BACKEND` | `local` / `azure` (`AZURE_STORAGE_CONNECTION_STRING`) / `supabase` |
| `SUPABASE_URL` / `SUPABASE_PUBLISHABLE_KEY` | sign-in; the client needs the same two as `NEXT_PUBLIC_*` |
| `SUPABASE_SERVICE_ROLE_KEY` | only for `STORAGE_BACKEND=supabase` |

Schema changes: edit `server/store/models.py`, then `uv run alembic revision --autogenerate -m "..."` and review the
generated file.

## Monitoring

Every part is off until its values are set in `.env.production` (and `client/.env.production` for the web app), so
local development needs none of it. Each piece sits on an open standard, so swapping a vendor is a config change.

### Tools

| What | Tool | How it's wired | Swap by |
|---|---|---|---|
| LLM calls | Langfuse | the app's own OpenTelemetry spans (each interview, every LLM call with messages, reply, model, tokens) over OTLP to Langfuse | `LANGFUSE_*`; any OTLP tool that reads `gen_ai.*` attributes works with small changes in `server/telemetry.py` |
| Errors | Sentry | `SENTRY_DSN` (gateway), `NEXT_PUBLIC_SENTRY_DSN` in `client/.env.production` (web app) | a GlitchTip DSN (same SDK) |
| Uptime | Sentry Uptime Monitoring | set up in Sentry, no code | — |
| Notifications | Slack | `server/notify.py`: sign-ups, contact messages, gateway starts to `SLACK_WEBHOOK_URL`; failures to `SLACK_ALERTS_WEBHOOK_URL` with `@channel` | a `_send_<name>` function + `NOTIFY_BACKENDS` |
| Logs | `docker compose logs` | JSON lines (`LOG_FORMAT=json`) with the interview and user id on every line | ship stdout with any log agent |
| Traces + metrics (optional) | any OTLP backend | `OTEL_ENDPOINT` / `OTEL_HEADERS`: HTTP requests, LLM provider calls, active calls, turn latency, errors, outcomes | the same two values |

LLM calls are named by what they are for (`interviewer`, `score_answer`, `cv_structure`, `jd_check`, `cv_questions`)
and grouped per interview as a Langfuse session. `LANGFUSE_CAPTURE_CONTENT=false` keeps prompts and replies out
(timings, tokens and cost only).

### One-time setup

1. **Slack**: create `#alerts` and `#activity`, then a Slack app with an incoming webhook for each; the URLs go in
   `SLACK_ALERTS_WEBHOOK_URL` / `SLACK_WEBHOOK_URL`.
2. **Langfuse**: project > Settings > API keys into `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`;
   `LANGFUSE_BASE_URL` is your data region's host.
3. **Sentry**: a Python project and a Next.js project; DSNs into `SENTRY_DSN` and `client/.env.production`'s
   `NEXT_PUBLIC_SENTRY_DSN`. Add its Slack integration (alerts to `#alerts`) and an uptime monitor on
   `https://api.<domain>/health`.

## Profiling (GPU)

### Latency benchmark

Real WebSocket traffic against a running gateway, p50/p95 per stage:

```bash
uv run python -m eval.latency_bench --host localhost --port 8000 --wav /tmp/test_sample.wav --turns 5
```

### GPU utilization

Run in a separate terminal alongside a load test (needs `nvidia-smi`):

```bash
uv run python -m eval.gpu_util_log --duration 60 --out eval/results/gpu_util.csv
```

### Kernel traces

`torch.profiler` trace of vLLM's offline Python API (kernel-level CPU+CUDA breakdown). Run it directly on the GPU box
with `uv add vllm`, not in a container:

```bash
uv run python -m eval.profile_llm_torch --model Qwen/Qwen2.5-1.5B-Instruct --out eval/results
```

For a system-level CUDA trace, wrap `vllm serve` with NVIDIA Nsight Systems
(`nsys profile -o run1 -- vllm serve ...`). Install the Nsight Systems CLI matching the box's CUDA/OS version from
[NVIDIA's download page](https://developer.nvidia.com/nsight-systems).

### Optimization order

Cheapest first: quantization (`--quantization awq`/`fp8`) → `--max-num-seqs` tuning → `--enable-prefix-caching`.
Capture `latency_bench` + `gpu_util_log` before and after each change.

## Tests

### Unit checks

Self-check scripts that run on fakes (no models, no network), the same set CI runs:

```bash
for t in test_store test_anonymize test_voice_anon test_interview test_agent test_markdown_strip test_session test_resume test_openai_audio test_silence test_monitoring; do
  uv run python -m tests.$t
done
```

### Integration

Real STT/LLM/TTS over an actual WebSocket:

```bash
uv run python -m tests.test_ws_integration
```

## Roadmap

- [ ] Encodec compression on the audio path
- [ ] Speech eval framework: WER, latency percentiles, NISQA, throughput
- [ ] More interview packs (technical, sales, healthcare and other niches)

Ideas and pack contributions are welcome: open an issue.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Can't reach the interview server" in the web app | the gateway isn't running on `:8000`, or `NEXT_PUBLIC_GATEWAY_WS_URL` points elsewhere |
| Calls refused with "all lines busy" | `MAX_SESSIONS` reached; raise it if the machine has headroom |
| Slow or laggy replies on CPU | use a smaller `WHISPER_MODEL` (`base.en` / `tiny.en`) and a fast LLM endpoint |
| No mic audio | the browser needs mic permission, and a secure origin (`https` or `localhost`) |
| `next build` fails on deleted pages | stale build cache: `rm -rf client/.next` |
| vLLM container can't see the GPU | install `nvidia-container-toolkit` on the host |

## Contributing

Issues and pull requests are welcome. For a large change, open an issue first to agree on the approach.

1. Fork the repo and create a branch.
2. Make your change, matching the style of the code around it.
3. Run the [tests](#tests) and `cd client && npm run build`.
4. Open a pull request with a short description of what and why.

Adding an interview niche only needs a new pack file in `packs/` (see `packs/tech_behavioral.toml`); packs are
validated at startup. Never commit secrets or real CVs. Full guide: [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please don't report security issues in public issues. Use GitHub's private vulnerability reporting (the repository's
**Security** tab, then **Report a vulnerability**). Details: [SECURITY.md](SECURITY.md).

If you run your own instance: keep `.env*` files out of git (they are ignored by default), use `https`, and review the
privacy and terms templates before inviting users.

## Acknowledgements

Built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Kokoro](https://github.com/hexgrad/kokoro),
[Silero VAD](https://github.com/snakers4/silero-vad), [Microsoft Presidio](https://github.com/microsoft/presidio),
[Parselmouth](https://github.com/YannickJadoul/Parselmouth), [FastAPI](https://fastapi.tiangolo.com),
[Next.js](https://nextjs.org), [Ollama](https://ollama.com) and [vLLM](https://github.com/vllm-project/vllm).

## License

[MIT](LICENSE)
