import { BRAND } from "@/lib/site";
import { PRIMARY, STANDALONE } from "@/lib/ui";

export default function NotFound() {
  return (
    <main className={`${STANDALONE} flex flex-col items-center justify-center px-4 text-center`}>
      <title>{`Page not found · ${BRAND}`}</title>
      <p className="text-6xl font-bold text-ink tabular-nums">404</p>
      <h1 className="mt-3 text-xl font-semibold text-ink">This page doesn&apos;t exist</h1>
      <p className="mt-1 max-w-sm text-ink-secondary">The link may be old, or the page was moved or removed.</p>
      <a href="/" className={`${PRIMARY} mt-6 inline-block`}>
        Go to the home page
      </a>
    </main>
  );
}
