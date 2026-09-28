// Selectable voices. Mirrors the server's TTS_VOICES allowlist, which re-validates every request.
// Each voice carries its orb palette: [light, mid, deep, darkest].

export type Palette = [string, string, string, string];

export interface Voice {
  id: string;
  name: string;
  description: string;
  palette: Palette;
}

export const VOICES: Voice[] = [
  { id: "af_heart", name: "Heart", description: "Warm and friendly", palette: ["#e0f7fa", "#4db6ac", "#00897b", "#00695c"] },
  { id: "af_bella", name: "Bella", description: "Bright and upbeat", palette: ["#f3e5f5", "#ba68c8", "#8e24aa", "#6a1b9a"] },
  { id: "am_michael", name: "Michael", description: "Calm and clear", palette: ["#e3f2fd", "#64b5f6", "#1e88e5", "#1565c0"] },
  { id: "am_fenrir", name: "Fenrir", description: "Deep and steady", palette: ["#fff8e1", "#ffb74d", "#f57c00", "#e65100"] },
];

export const DEFAULT_VOICE = VOICES[0];

const STORAGE_KEY = "voice";

export function loadVoice(): Voice {
  try {
    return VOICES.find((v) => v.id === localStorage.getItem(STORAGE_KEY)) ?? DEFAULT_VOICE;
  } catch {
    return DEFAULT_VOICE;
  }
}

export function saveVoice(voice: Voice): void {
  try {
    localStorage.setItem(STORAGE_KEY, voice.id);
  } catch {
    // storage blocked: the choice just won't persist
  }
}
