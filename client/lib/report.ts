// Shape of the scoring report (server/agent/scoring.py) and how the report page reads it.
import type { ShareChoices } from "./share";

export interface Turn {
  role: "user" | "assistant";
  text: string;
  start: number; // epoch seconds (server clock)
  end: number;
}

export interface Delivery {
  words: number;
  speech_s: number;
  wpm: number;
  fillers: number;
  fillers_per_min: number;
  avg_latency_s: number | null;
  talk_ratio?: number | null;
  avg_answer_s?: number;
  longest_answer_s?: number;
}

export interface Answer {
  index: number;
  question: string;
  source: "bank" | "cv" | "jd_gap";
  cv_ref: string;
  answer_text: string;
  turns: Turn[];
  delivery: Delivery;
  scored: boolean;
  score: number | null;
  scores?: Record<string, number>;
  evidence?: Record<string, string>;
  strengths?: string[];
  improvements?: string[];
  improved_answer?: string;
  cv_alignment?: string;
  // Civil Service (Success Profiles) reports only
  element?: "behaviour" | "strength" | "experience";
  label?: string;
  met?: string[];
  missed?: string[];
}

export interface Report {
  status: "scored" | "failed";
  pack_name: string;
  role: string;
  seniority: string;
  delivery: Delivery;
  rubric?: { name: string; description: string }[];
  answers: Answer[];
  overall_score?: number;
  verdict?: string;
  dimensions?: Record<string, number>;
  top_strength?: string;
  top_fix?: string;
  error?: string;
  mode?: "success_profiles"; // absent: the generic 0-100 report
  average?: number; // Civil Service: mean score out of 7
  scale?: Record<string, string>; // Civil Service: "1".."7" -> label
}

export interface SessionDetail {
  id: string;
  pack_id: string;
  elements: { behaviours: string[]; strengths: boolean; experience: boolean } | null;
  interview_date: string | null;
  role: string;
  seniority: string;
  status: "created" | "live" | "scoring" | "scored" | "failed" | "abandoned";
  overall_score: number | null;
  verdict: string | null;
  created_at: string;
  report: Report | null;
  has_recording: boolean;
  recording_status: "processing" | "ready" | "failed" | null; // null: recorded before voice disguise
  audio_started_at: number | null;
  share: { slug: string | null; choices: ShareChoices | null };
  suggested_name: string;
}

export const LEVEL_LABEL: Record<string, string> = { junior: "Entry level", mid: "Mid level", senior: "Senior" };

export const SOURCE_LABEL: Record<Answer["source"], string> = {
  bank: "Common question",
  cv: "From your CV",
  jd_gap: "Job gap",
};

// Same list as server/agent/scoring.py FILLERS; keep them in sync.
export const FILLER_RE = /\b(?:um+|uh+|erm|hmm+|you know|i mean|kind of|sort of|basically|actually|literally)\b/gi;

export const humanize = (name: string) => name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

// Delivery targets for spoken interview answers. One place to tune them.
export type Verdict = "good" | "work";
export interface Metric {
  label: string;
  value: string;
  hint: string;
  verdict: Verdict | null; // null: not enough data to judge
}

const within = (v: number | null | undefined, lo: number, hi: number): Verdict | null =>
  v === null || v === undefined ? null : v >= lo && v <= hi ? "good" : "work";

export function deliveryMetrics(d: Delivery): Metric[] {
  const secs = (v?: number | null) => (v === null || v === undefined ? "—" : `${Math.round(v)}s`);
  return [
    { label: "Speaking pace", value: `${d.wpm} wpm`, hint: "Aim for 130–160 words per minute.", verdict: d.speech_s ? within(d.wpm, 130, 160) : null },
    { label: "Filler words", value: `${d.fillers_per_min}/min`, hint: "Under 3 per minute sounds confident.", verdict: d.speech_s ? within(d.fillers_per_min, 0, 3) : null },
    { label: "Average answer", value: secs(d.avg_answer_s), hint: "60–150 seconds fits a full story.", verdict: within(d.avg_answer_s, 60, 150) },
    { label: "Longest answer", value: secs(d.longest_answer_s), hint: "Keep any answer under 3 minutes.", verdict: within(d.longest_answer_s, 0, 180) },
    { label: "Response time", value: secs(d.avg_latency_s), hint: "Start within about 3 seconds; a short pause is fine.", verdict: within(d.avg_latency_s, 0, 3) },
    {
      label: "Your share of talk",
      value: d.talk_ratio === null || d.talk_ratio === undefined ? "—" : `${Math.round(d.talk_ratio * 100)}%`,
      hint: "The candidate should talk most: 55–75%.",
      verdict: within(d.talk_ratio, 0.55, 0.75),
    },
  ];
}
