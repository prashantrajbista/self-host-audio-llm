"use client";

import { createClient, type Session } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import { gatewayHttpUrl } from "./ws";

// Auth only (sign-in, access tokens). All data goes through the gateway API (gatewayFetch).
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "",
);

// Current auth session: undefined while loading, null when signed out.
export function useAuth(): Session | null | undefined {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);
  return session;
}

// Redirect to /login when signed out; returns the session once known.
export function useRequireAuth(): Session | null | undefined {
  const session = useAuth();
  useEffect(() => {
    if (session === null) window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
  }, [session]);
  return session;
}

export class GatewayError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

// Gateway HTTP call as the signed-in user. Throws GatewayError with the server's message (shown to the user).
export async function gatewayFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const res = await fetch(gatewayHttpUrl(path), {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${data.session?.access_token ?? ""}` },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new GatewayError(typeof body.detail === "string" ? body.detail : "Something went wrong. Try again.", res.status);
  return body as T;
}

export interface CvProfile {
  name?: string;
  headline?: string;
  years_experience?: number;
  roles?: { company?: string; title?: string; dates?: string; achievements?: string[] }[];
  probe_points?: { claim: string; why: string }[];
}

export interface Cv {
  id: string;
  file_name: string;
  cv_profile: CvProfile | null;
  created_at: string;
  anon_text?: string; // only right after upload: the anonymized text the AI works from
}

export interface Profile {
  credits: number;
  has_pass: boolean;
}

export interface InterviewSession {
  id: string;
  pack_id: string;
  role: string;
  seniority: string;
  interview_type: string;
  status: "created" | "live" | "scoring" | "scored" | "failed" | "abandoned";
  overall_score: number | null;
  verdict: string | null;
  created_at: string;
  dimensions?: Record<string, number> | null; // scored only: skill averages, 1-5
  rubric?: Record<string, string>; // scored only: skill -> what it measures
  average?: number | null; // scored Civil Service interviews: mean score out of 7
}
