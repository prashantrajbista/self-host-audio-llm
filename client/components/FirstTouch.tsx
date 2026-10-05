"use client";

import { useEffect } from "react";
import { gatewayFetch, supabase } from "@/lib/supabase";

const KEY = "first_touch"; // where this browser first arrived from; sent once after sign-in
const SENT = "first_touch_sent";
const UTM = ["utm_source", "utm_medium", "utm_campaign"] as const;

// Records the landing page, referring site and utm_* of the first visit, so sign-ups, mocks and payments can be
// traced to the page and channel that brought them (server/funnel.py). Only the referrer's host is kept.
export function FirstTouch() {
  useEffect(() => {
    try {
      if (!localStorage.getItem(KEY)) {
        const params = new URLSearchParams(window.location.search);
        const ref = document.referrer ? new URL(document.referrer).host : "";
        const touch: Record<string, string> = {
          landing: window.location.pathname.slice(0, 200),
          referrer: ref === window.location.host ? "" : ref.slice(0, 200),
        };
        for (const k of UTM) touch[k] = (params.get(k) ?? "").slice(0, 100);
        localStorage.setItem(KEY, JSON.stringify(touch));
      }
    } catch {
      return; // storage blocked: no attribution for this visitor
    }
    const send = () => {
      try {
        if (localStorage.getItem(SENT)) return;
        const touch = localStorage.getItem(KEY);
        if (!touch) return;
        gatewayFetch("/me/attribution", { method: "POST", headers: { "Content-Type": "application/json" }, body: touch }).then(
          () => localStorage.setItem(SENT, "1"),
          () => {},
        );
      } catch {
        // storage blocked
      }
    };
    const { data } = supabase.auth.onAuthStateChange((_event, s) => s && send());
    return () => data.subscription.unsubscribe();
  }, []);
  return null;
}
