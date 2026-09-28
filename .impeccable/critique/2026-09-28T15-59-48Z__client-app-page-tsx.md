---
target: client/app/page.tsx (voice agent UI)
total_score: 16
max_score: 36
na_heuristics: 7
p0_count: 2
p1_count: 2
timestamp: 2026-09-28T15-59-48Z
slug: client-app-page-tsx
---
Method: dual-agent (A: design-review subagent · B: detector-evidence subagent)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | No "connecting" state — button grays out, Orb stays idle, silence in between. Error text is small and inline (`text-red-400 text-sm`, page.tsx:16), easy to miss. |
| 2 | Match System / Real World | 2 | "Listening…" and color-coded Orb states are intuitive, but nothing signals full-duplex/bidirectional streaming or barge-in — reads as turn-based chat with a loader. |
| 3 | User Control and Freedom | 1 | No stop/cancel/pause/hang-up button. Transcript can't be cleared. No escape from a stuck connecting state. |
| 4 | Consistency and Standards | 3 | Consistent Orb palette and standard Tailwind states. Minor tension: `text-center` transcript container against `text-left` markdown lists (Transcript.tsx:12). |
| 5 | Error Prevention | 1 | Mic permission request fires with zero in-UI warning — the browser's native modal is the only signal. No pre-flight explanation, no retry affordance on failure. |
| 6 | Recognition Rather Than Recall | 3 | Orb states are visually distinct, button text is explicit, no hidden modes. |
| 7 | Flexibility and Efficiency of Use | n/a | Single-action demo (one button, no workflows) — the heuristic doesn't apply to this surface. |
| 8 | Aesthetic and Minimalist Design | 3 | Clean, centered, generous spacing. Gap: transcript container (Transcript.tsx:24) has `max-w-md` but no `overflow-y-auto` — a long reply pushes the button/orb off-screen. |
| 9 | Error Recovery | 1 | Errors are plain small red text with no specific guidance ("Microphone access denied. Check browser settings." doesn't exist) and no recovery action. |
| 10 | Help and Documentation | 0 | No tooltips, hints, or onboarding. The Orb's meaning is unexplained for sighted users — its `aria-label` is screen-reader only. |
| **Total** | | **16/36** | **Poor (44%)** |

Heuristic 7 scored n/a (single-action surface, no workflows to accelerate); total renormalized to /36.

## Design Specificity Verdict

**LLM assessment:** Partially specific, weakly differentiated. The Orb is a genuine anchor — its pulse rate visibly speeds up during active states (0.06 rad/frame) vs idle (0.015), which is real proof-of-liveness work most demos skip. But the button copy ("Start talking" / "Listening…") and layout (centered stack, dark background) are generic conversational-UI defaults. Nothing in the composition signals the actual differentiator — full-duplex streaming and barge-in interrupt — unless a visitor happens to try interrupting mid-reply and notices the Orb shift back to blue. A recruiter skimming for 10 seconds reads this as "chatbot with a nice loading animation," not "real-time voice-streaming engineering." For a CV-proof surface, the mechanism is exactly what should be legible and isn't.

**Deterministic scan:** `detect.mjs` ran clean across all 6 target files (page.tsx, layout.tsx, Orb.tsx, Transcript.tsx, ConnectButton.tsx, globals.css) — 0 findings, exit code 0. No false positives to note (nothing was flagged). This mainly reflects that the surface is too minimal/default to trip pattern-based slop detectors, not that it's well-designed — consistent with DESIGN.md's own assessment that this is unstyled Tailwind defaults, not a considered system.

**Visual overlays:** Unavailable — no browser automation tool exists in this session. No live overlay was generated; this is a source-only critique.

## Overall Impression

Functionally sound, cognitively simple (zero cognitive-load-checklist failures — genuinely well-scoped for a one-action surface), but visually and communicatively silent about the one thing this demo exists to prove. The Orb's pulse-rate work is the single best design decision here and it's under-leveraged: nothing tells a visitor what they're looking at, what just happened, or that they can interrupt the agent. The biggest opportunity is making the pipeline's real-time mechanics (state, interrupt, connection) as legible as the code that produces them.

## What's Working

1. **Orb pulse-rate differentiation** (Orb.tsx:40-42): faster pulse in active states vs. idle is intuitive, wordless proof the system is "alive" — better signal than a static spinner or icon.
2. **Single-action focus**: one button, no auth, no menus. A cold visitor understands the primary action in seconds — the cognitive-load checklist passes cleanly (0/8 failures).
3. **Markdown-rendered transcript** (Transcript.tsx): heading/bold/list/code treatment shows the reply is semantically real content, not a flat text dump.

## Priority Issues

**[P0] Mic permission request has zero forewarning**
- **Why it matters:** The browser's native permission modal appears with no in-UI lead-in. For a one-shot cold visit, an unexpected browser prompt reads as a bug or a trust red flag, not part of the experience.
- **Fix:** Add a line of copy near the button before first click ("Requires microphone access") or a one-step confirmation before requesting the permission.
- **Suggested command:** `/impeccable onboard`

**[P0] No visible "connecting" state**
- **Why it matters:** Between click and first Orb state change there's silence — button grays out, Orb stays idle. A recruiter on a cold demo link has no way to distinguish "working" from "broken," and will likely re-click or leave.
- **Fix:** Give the Orb (or a companion indicator) an explicit connecting state — distinct color/pulse — the moment the button is clicked, not after the WebSocket handshake completes.
- **Suggested command:** `/impeccable animate`

**[P1] Full-duplex/barge-in capability is invisible**
- **Why it matters:** This is the actual CV differentiator per PRODUCT.md, and nothing on screen states or demonstrates it. A visitor who doesn't happen to try interrupting mid-reply will never discover it.
- **Fix:** Add a short line near the button ("You can talk over it — try interrupting") and/or a distinct visual moment when barge-in is detected (not just the Orb quietly reverting to blue).
- **Suggested command:** `/impeccable clarify`

**[P1] Errors are easy to miss and unactionable**
- **Why it matters:** `text-red-400 text-sm` inline text is the only error surface. A recruiter on a locked-down corporate network who gets a connection failure sees a small gray-red line, not a clear "here's what happened, here's what to do."
- **Fix:** Promote errors to a more prominent treatment (larger text, or a toast/banner) with specific, actionable copy per failure mode (mic denied vs. connection failed vs. timeout).
- **Suggested command:** `/impeccable harden`

**[P2] Transcript has no scroll container**
- **Why it matters:** `max-w-md min-h-[2.5em]` with no `overflow-y-auto` (Transcript.tsx:24) — a sufficiently long reply pushes the Orb and button off-screen, breaking the surface mid-demo.
- **Fix:** Add `overflow-y-auto` with a `max-h` cap to the transcript container.
- **Suggested command:** `/impeccable layout`

## Persona Red Flags

**Jordan (First-Timer / recruiter, cold visit):** The Orb has no label or legend — a sighted first-timer sees an unexplained pulsing animation until they separately read the button text. The mic permission modal appears with no narrative lead-in, interrupting the flow right at the moment of commitment.

**Sam (Accessibility-Dependent):** Orb state is color-only (blue/orange/green/gray) — no luminosity separation or pattern backup, a real problem for deuteranopia/protanopia. `ConnectButton.tsx` has no visible `:focus-visible` override, so keyboard-only navigation loses track of focus. Transcript links open with no `rel`/warning noted for new-tab behavior.

## Minor Observations

1. Canvas isn't DPI-aware (`width={240} height={240}` with no `devicePixelRatio` scaling) — renders soft on Retina displays.
2. No session end/timeout signal — a conversation can stream indefinitely with no "end" state distinct from idle, leaving a visitor unsure if it's still working.
3. Page metadata is placeholder-tier (`<title>Voice Agent</title>`, generic description) — a missed chance to state the differentiator (full-duplex, barge-in) where a recruiter's browser tab / link preview would show it.

## Questions to Consider

1. If the Orb is the only visual signal of the system's core differentiator, and most visitors won't infer full-duplex/interrupt from it alone — should the Orb carry more explicit meaning, or should copy carry the claim instead?
2. Does the current error handling meet the bar for a piece meant to prove engineering rigor? Small red text next to a botton reads as unfinished, not robust.
3. What would actually prove — visually — that this is real voice streaming (STT→LLM→TTS) rather than typed-text-to-speech? A waveform, a VU meter, a visible latency number?
