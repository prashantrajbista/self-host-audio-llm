# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Recruiters, hiring managers, and technical interviewers evaluating the author for a Voice AI
Engineer role. Their job: open a shared URL, grant mic access, and have a live voice
conversation with the agent to assess real-time engineering skill — not a normal end-user
persona with recurring, unattended usage.

## Product Purpose

A live, working demonstration of full-duplex streaming voice-agent engineering (STT → LLM →
TTS with barge-in) backing a CV/job application, closing specific gaps against a target role's
stated requirements (serving-engine experience, GPU profiling, audio streaming, speech eval).
Success is a technical evaluator experiencing smooth real-time voice interaction while being
able to see the pipeline's live state, credibly demonstrating the claimed engineering skill —
not conversion, retention, or any normal product metric.

## Positioning

Unlike a typical "wrapped an API" chatbot demo, this exposes the actual serving-engine
mechanics: self-hosted STT/TTS, a swappable GPU-served LLM leg, VAD-driven barge-in, and
visible pipeline state. The mechanism itself — made visible — is the credibility signal, not
conversational quality alone.

## Operating Context

Opened via a shared URL, likely once, cold — no onboarding a normal evaluator would sit
through. Browser mic permission required. Talks to a gateway over WebSocket. Runs on the
author's own rented GPU box or local machine, so uptime/session limits are casual, not
guaranteed-uptime SaaS. Single active voice session per connection (no multi-tenant concurrency
model).

## Capabilities and Constraints

- Real-time full-duplex voice conversation (STT → LLM → TTS) with barge-in interrupt
- Pipeline state already surfaced over WebSocket: `state` (listening/thinking/speaking/idle),
  `partial_transcript`, streamed `token`s, `interrupt` — the UI's job is to make these legible,
  not to invent new backend signals
- No auth, no accounts, no persistence across sessions
- Requires mic access; browser-only (no native app)
- LLM backend swappable (OpenAI by default; self-hosted Ollama/vLLM optional) — UI should not
  assume one specific backend's latency characteristics

## Brand Commitments

None. Name and visual identity are fully open — no legacy identity to preserve. Casual
startup-name brainstorming earlier in this project (Voicewire, Murmur, Latch, Echofrom, Barge)
is not binding; design work may propose its own direction.

## Evidence on Hand

- `docs/voice-ai-project.md` — project brief and CV framing (source of the purpose/positioning
  facts above)
- `README.md` — architecture and setup
- Existing minimal UI: `Orb.tsx` (state-driven visual), `Transcript.tsx` (live streamed,
  markdown-rendered transcript), `ConnectButton.tsx`
- No user research, testimonials, or case studies exist — future work must not fabricate any

## Product Principles

1. Live pipeline state (listening/thinking/speaking/barge-in) is the core credibility signal —
   keep it visible and legible, never collapse it into a generic "AI is thinking" indicator.
2. Optimize for a cold, unassisted first encounter — one shot, no walkthrough, no accounts, no
   friction before mic permission.
3. Live-conversation reliability over feature breadth — latency and responsiveness read
   directly as engineering competence in this context.
4. Minimal chrome, honest about scope — don't dress up known limitations (single session, no
   auth) as a polished SaaS product.
5. Visual identity is a blank canvas — no legacy brand debt; free to establish a new visual
   world.
