import { LEGAL_UPDATED } from "@/lib/site";

export function LegalPage({ title, dated = true, children }: { title: string; dated?: boolean; children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
      <h1 className="text-[2.125rem] font-bold leading-tight text-ink text-balance">{title}</h1>
      {dated && <p className="mt-2 text-sm text-ink-secondary">Last updated {LEGAL_UPDATED}</p>}
      {dated && (
        <p className="mt-4 rounded-[12px] bg-primary/10 px-4 py-3 text-sm text-ink">
          Template for self-hosted instances. Whoever runs this site must review it and fill in their own details before
          going live.
        </p>
      )}
      <div className="prose-page mt-8 text-ink">{children}</div>
    </main>
  );
}
