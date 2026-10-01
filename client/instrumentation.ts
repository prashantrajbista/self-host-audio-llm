// Server side of the Next.js app (instrumentation): errors in server rendering go to Sentry, when configured.
import * as Sentry from "@sentry/nextjs";

export function register() {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (dsn) Sentry.init({ dsn, environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development", tracesSampleRate: 0 });
}

export const onRequestError = Sentry.captureRequestError;
