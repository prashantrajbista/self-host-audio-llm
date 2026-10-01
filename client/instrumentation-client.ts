// Runs before the app in the browser (Next.js instrumentation-client). Error reports to Sentry, or GlitchTip
// (same DSN format), only when NEXT_PUBLIC_SENTRY_DSN is set. No performance tracing and no session replay.
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({ dsn, environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development", tracesSampleRate: 0 });
}
