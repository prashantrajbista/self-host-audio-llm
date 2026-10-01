"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { PRIMARY, SECONDARY, STANDALONE } from "@/lib/ui";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
    Sentry.captureException(error); // no-op unless Sentry is configured (instrumentation-client.ts)
  }, [error]);
  return (
    <main className={`${STANDALONE} flex flex-col items-center justify-center px-4 text-center`}>
      <h1 className="text-xl font-semibold text-ink">Something went wrong on this page</h1>
      <p className="mt-1 max-w-sm text-ink-secondary">Try again. If it keeps happening, reload the page or come back in a few minutes.</p>
      <div className="mt-6 flex gap-3">
        <button onClick={reset} className={PRIMARY}>
          Try again
        </button>
        <a href="/" className={SECONDARY}>
          Home
        </a>
      </div>
    </main>
  );
}
