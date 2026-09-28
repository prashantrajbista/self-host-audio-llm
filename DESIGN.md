---
name: Voice Agent
description: Live full-duplex voice agent demo — white-dominant, teal accent, Apple system typography
colors:
  neutral-bg: "#f5f5f7"
  neutral-surface: "#ffffff"
  text-primary: "#1d1d1f"
  text-secondary: "#6e6e73"
  border: "#d2d2d7"
  primary: "#00695c"
  primary-hover: "#004d40"
  state-idle: "#80cbc4"
  state-listening: "#26a69a"
  state-thinking: "#00695c"
  state-speaking: "#00bfa5"
  state-disconnected: "#c9c9c9"
  state-connecting: "#26a69a"
  text-error: "#ff3b30"
  text-link: "#007aff"
typography:
  headline-lg:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif"
    fontSize: "2.125rem"
    fontWeight: 700
    lineHeight: 1.15
  headline-md:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.2
  headline-sm:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.25
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    letterSpacing: "normal"
rounded:
  full: "9999px"
  md: "12px"
spacing:
  md: "16px"
  lg: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.full}"
    padding: "12px 28px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
---

# Design System: Voice Agent

## Overview

**Creative North Star: "System Preferences, with a Realtime Orb"**

A white-dominant surface built from Apple's own visual vocabulary — the SF system font stack,
Apple's near-black text, Apple's off-white `#f5f5f7` ground — fused with a second, explicitly
requested reference: the soft, morphing, glowing sphere from ChatGPT's realtime voice mode,
rebuilt in teal. Color strategy: **Committed on the orb** — teal carries both the primary button
and the orb itself, unified as one brand mark rather than diluted across unrelated hues.
Everything else on the page (text, background, dividers) stays neutral — the commitment is
concentrated, not spread thin.

This supersedes three prior passes — bare-Tailwind dark baseline, Apple-palette (multi-hue
System Colors, flat circle), and warm-orange blob orb — see git history for all three
snapshots. The client code has been rebuilt to match this file.

**Key Characteristics:**
- White-dominant (`#f5f5f7` ground, `#ffffff` surfaces), no dark mode
- Teal (`#00695c` family) is the single committed color, carried by both the primary button and
  the orb
- The orb is a solid sphere with a crisp edge and soft internal cloud-light movement (the
  ChatGPT-realtime-voice reference), not a flat pulsing circle
- Pipeline states differentiate through motion character and brightness (idle slow/dim, thinking
  fast/turbulent, speaking large-amplitude "breathing"), not through hue-swapping — the orb stays
  one consistent teal mark rather than becoming a mood ring
- Apple's SF system font stack throughout; near-black (`#1d1d1f`) text, not pure black
- Minimal elsewhere: few colors outside the orb, generous whitespace, soft/diffused shadows only
  where they earn their place

## Colors

**The One Family Rule.** Teal is the surface's only saturated color family — carried by the
primary button (`#00695c` flat) and the orb (a `#004d40`–`#e0f7fa` gradient range, deep teal to
pale mint). A color outside that family anywhere else (a state indicator in orange, a link in
green) dilutes the mark back into decoration. The orb's tonal range within teal is not an
exception to this — it's the same family at different lightness/saturation, not a second accent.

### Primary
- **Deep Teal** (`#00695c`): the connect button's background, flat — the button reads as a
  solid, tappable object distinct from the orb's soft glow.

**The Light-on-Teal Rule.** Near-black text on `#00695c` measures only ~3.90:1 — under the
4.5:1 body-text floor. White text measures ~6.61:1, comfortably clear. Unlike the orange pass,
this button uses **white** text — teal is dark enough at this saturation that white, not ink, is
the accessible choice. Always recompute contrast per hue; don't carry the previous palette's
text-color rule forward blind.

### Neutral
- **Apple off-white** (`#f5f5f7`): page background — Apple's own marketing-site ground tone, not
  pure white, easier on the eyes at rest.
- **Pure white** (`#ffffff`): any elevated surface, and the primary button's text.
- **Near-black** (`#1d1d1f`): primary text — Apple never uses pure `#000000` for text; this is
  their documented label color.
- **Secondary gray** (`#6e6e73`): secondary/helper text (the mic-permission note, the full-duplex
  line).
- **Border gray** (`#d2d2d7`): any hairline divider or outline, used sparingly.

### Pipeline states (orb sphere tones — see Components → Orb for the motion side of each)
- **Idle** (`#e0f7fa` → `#4db6ac`, pale mint to muted teal, muted, slow breathing)
- **Listening** (`#e0f7fa` → `#00897b`, mint to teal, moderate breathing)
- **Thinking** (`#b2dfdb` → `#004d40`, deepest teal, fastest and most turbulent)
- **Speaking** (`#e0f7fa` → `#00897b` with a `#00bfa5` vivid-emerald mid-tone, brightest,
  largest breathing amplitude — "color coming and going while talking")
- **Connecting** (`#e0f7fa` → `#00897b` plus a rotating arc overlay): the handshake/mic-permission
  window between clicking "Start talking" and the first real state — the arc is a shape change,
  not just a color, so it reads as distinct even within the same teal family.
- **Disconnected** (`#d8d8d8` → `#c9c9c9`, neutral gray, nearly static): the deliberate exception
  to The One Family Rule — "off" is not a pipeline moment, so it doesn't earn the brand color.

### Feedback
- **Error red** (`#ff3b30`, systemRed): connection/permission error text.
- **Link blue** (`#007aff`, systemBlue): the one non-teal, non-neutral color on the page — links
  read as "system blue" by web convention regardless of brand accent, and blue sits far enough
  from teal on the wheel that neither reads as a variant of the other.

## Typography

**Font:** `-apple-system, BlinkMacSystemFont, "SF Pro Text"/"SF Pro Display", system-ui,
sans-serif` — Apple's real system stack. Renders as actual San Francisco on macOS/iOS/Safari;
falls back to each platform's own system font elsewhere (Segoe UI on Windows, Roboto on
Android/Chrome OS) rather than a webfont download — appropriate for this Operate-mode surface,
and zero licensing or self-hosting to manage.

**Character:** Apple's own type voice — semibold (600) headlines rather than heavy bold in most
places, a body size of 17px (Apple's canonical reading size, not the web's default 16px), and
near-black rather than pure-black ink.

### Hierarchy
- **Headline lg** (700, 2.125rem, 1.15 line-height): reserved for a page-level title if one is
  ever added; currently unused live.
- **Headline md** (700, 1.375rem): markdown `h1` in the transcript.
- **Headline sm** (600, 1.25rem): markdown `h2`/`h3` in the transcript (semibold, not bold —
  the Apple "Headline" style, distinct from Title weight).
- **Body** (400, 1.0625rem / 17px): transcript paragraph text — Apple's canonical body size.
- **Label** (600, 0.9375rem): button and helper-line text — semibold, Apple's "Subhead" weight.

## Layout

Unchanged from the prior baseline: single centered column, `flex flex-col items-center
justify-center gap-8`, `min-h-screen`, `px-4` page padding, `max-w-md` cap on the transcript.
No responsive breakpoints are defined yet — still an open gap, not resolved by any color pass.

## Elevation & Depth

**The Soft-Only Rule, for chrome.** Where a *UI surface* needs depth (a card, a panel), it is a
large, low-opacity, blur-only shadow — never a hard offset, never a colored glow standing in for
a shadow.

- **Ambient** (`box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08)`): the one shadow role for any future
  elevated chrome surface. Nothing in the current component set uses it yet.

**The orb is the named exception**, not a violation of the rule above: its soft internal
cloud-light material is the whole point of the ChatGPT-realtime-orb reference, and it lives in
canvas, not CSS box-shadow. The rule governs interface chrome; the orb is content/identity, the
same way a product photo or illustration would be exempt from a chrome shadow rule.

## Shapes

Unchanged: fully-rounded (`rounded-full`, `9999px`) for the orb and the button. `rounded.md`
(`12px`) stays in the token set for any future rectangular surface (a card, an input) — Apple's
own corner language uses continuous/squircle-leaning moderate radii for rectangular elements,
reserving full pill shapes for buttons and avatars, not for every container.

## Components

### Orb
The signature piece — a solid sphere with a crisp edge and soft internal cloud-light movement
(the ChatGPT-realtime-voice reference, recolored teal). Size is fixed; only the internal light
animates. Three layers, in order:

1. **Base** — a radial gradient (highlight offset upper-left, like a lit ball) drawn crisp, no
   blur, giving the sphere its solid form and edge.
2. **Internal clouds** (2 layers) — soft, blurred, independently drifting radial gradients,
   blended additively (`globalCompositeOperation: "lighter"`) and clipped to the same circular
   path as the base, so the blur is masked at the sphere's boundary and never bleeds past it
   (canvas filters are confined by the active clip at fill time — this is what keeps the edge
   crisp while the interior stays soft).
3. **Breathing opacity** — the clouds' alpha oscillates over time (`STATE_CONFIG`'s
   `breathSpeed`/`breathMin`/`breathMax`), so the internal color visibly comes and goes rather
   than sitting static. Fastest and highest-amplitude while speaking (per the request: "color
   coming and going while talking"); slowest and dimmest at idle.

Per-state config varies **breathing speed/amplitude and cloud-drift speed** — not hue — since
all states share the teal family (see Colors → Pipeline states). `connecting` adds a rotating
arc outside the sphere's edge (a shape cue, since the sphere alone can't carry a fifth distinct
read within one hue family). The barge-in flash ring stays ink-colored (`rgba(29,29,31,…)`) —
visible against both the white ground and the teal sphere alike.

### Buttons
- **Shape:** fully rounded (`rounded-full`)
- **Primary:** `#00695c` background, **white** text (`#ffffff` — see The Light-on-Teal Rule),
  `px-7 py-3` (28px/12px)
- **Hover:** `#004d40` (a step darker — pressed-into-the-surface feel)
- **Disabled:** `#d2d2d7` (border-gray) fill, `#6e6e73` text, `cursor-not-allowed`

### Transcript
Unchanged structurally (markdown-rendered, centered, `max-w-md`); body text `#1d1d1f`
(near-black), link color `#007aff` (systemBlue), inline code on a low-opacity divider-gray chip.

## Do's and Don'ts

### Do:
- **Do** treat this file as the committed direction — it's built, not a placeholder.
- **Do** keep teal the only saturated color family (The One Family Rule) — the orb's internal
  tonal range doesn't violate this, a genuinely different hue would.
- **Do** keep pipeline state legible through motion/brightness when adding a new state — still
  the product's core credibility signal per `PRODUCT.md`; don't reach for a new hue to solve it.
- **Do** recompute contrast per hue before reusing a text-color rule from a prior palette pass —
  see The Light-on-Teal Rule for why orange's "always ink text" rule didn't carry over.

### Don't:
- **Don't** add a color outside the teal family anywhere on the surface (link blue is the one
  named exception — see Colors → Feedback).
- **Don't** put near-black text on `#00695c` — it only measures ~3.90:1, under the 4.5:1 floor.
  Use white.
- **Don't** apply the chrome Soft-Only shadow rule to the orb — it's the named exception, not a
  loophole to extend to buttons/cards.
- **Don't** reintroduce hardcoded hex values in component classNames outside `Orb.tsx` (canvas
  drawing needs real hex, not Tailwind classes) — everything else uses the real theme tokens in
  `tailwind.config.ts`.
