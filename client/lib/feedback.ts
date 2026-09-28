// Short synthesized cues + haptics for call events. Own AudioContext (created on first use)
// because the call's playback context is closed at hang-up, before the "end" cue plays.

export type FeedbackKind = "connect" | "end" | "interrupt" | "error";

const STORAGE_KEY = "feedback-enabled";

// [frequency Hz, start offset s, duration s] per note
const TONES: Record<FeedbackKind, [number, number, number][]> = {
  connect: [
    [660, 0, 0.09],
    [880, 0.1, 0.12],
  ],
  end: [
    [880, 0, 0.09],
    [520, 0.1, 0.14],
  ],
  interrupt: [[440, 0, 0.06]],
  error: [
    [220, 0, 0.1],
    [220, 0.16, 0.1],
  ],
};

const VIBRATION: Record<FeedbackKind, number[]> = {
  connect: [15],
  end: [20, 40, 20],
  interrupt: [10],
  error: [40, 60, 40],
};

let ctx: AudioContext | null = null;

export function feedbackEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== "off";
  } catch {
    return true;
  }
}

export function setFeedbackEnabled(on: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // storage blocked: the setting just won't persist
  }
}

export function feedback(kind: FeedbackKind): void {
  if (!feedbackEnabled()) return;
  navigator.vibrate?.(VIBRATION[kind]);
  try {
    ctx ??= new AudioContext();
    const now = ctx.currentTime;
    for (const [freq, offset, duration] of TONES[kind]) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      // quick attack, exponential decay: a soft blip rather than a click
      gain.gain.setValueAtTime(0.0001, now + offset);
      gain.gain.exponentialRampToValueAtTime(0.08, now + offset + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + duration);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now + offset);
      osc.stop(now + offset + duration + 0.02);
    }
  } catch {
    // audio unavailable: cues are optional
  }
}
