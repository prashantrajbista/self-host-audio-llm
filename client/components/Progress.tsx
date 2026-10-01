import { humanize } from "@/lib/report";
import type { InterviewSession } from "@/lib/supabase";

const FOCUS_WINDOW = 3; // weakest skill is judged on the last few mocks, not all-time

// Score trend across scored mocks: overall line, per-skill latest + change since the first, and what to work on next.
export function Progress({ rows }: { rows: InterviewSession[] }) {
  const scored = rows.filter((r) => r.status === "scored" && r.dimensions && r.overall_score !== null).reverse(); // oldest first
  if (scored.length < 2) return null;
  const first = scored[0];
  const latest = scored[scored.length - 1];
  const skills = Object.keys(latest.dimensions!);
  const recent = scored.slice(-FOCUS_WINDOW);
  const avg = (skill: string) => recent.reduce((sum, r) => sum + (r.dimensions![skill] ?? 0), 0) / recent.length;
  const focus = skills.reduce((low, s) => (avg(s) < avg(low) ? s : low));
  const overall = scored.map((r) => r.overall_score!);

  return (
    <section aria-labelledby="progress" className="mt-6 rounded-[12px] bg-bg p-5">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="progress" className="font-semibold text-ink">
          Your progress
        </h2>
        <span className="text-sm text-ink-secondary">{scored.length} scored mocks</span>
      </div>
      <div className="mt-3 flex items-end gap-4">
        <p className="text-3xl font-bold text-ink tabular-nums">
          {latest.overall_score}
          <span className="text-base font-normal text-ink-secondary">/100</span>
        </p>
        <Change value={latest.overall_score! - first.overall_score!} digits={0} />
        <Spark values={overall} min={0} max={100} className="ml-auto h-10 w-40" label={`Overall score over time: ${overall.join(", ")}`} />
      </div>
      <ul className="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {skills.map((s) => {
          const values = scored.map((r) => r.dimensions![s] ?? 0);
          return (
            <li key={s} className="flex items-center gap-3 text-sm">
              <span className="w-24 text-ink">{humanize(s)}</span>
              <span className="w-8 font-semibold text-ink tabular-nums">{latest.dimensions![s].toFixed(1)}</span>
              <Change value={latest.dimensions![s] - first.dimensions![s]} digits={1} />
              <Spark values={values} min={1} max={5} className="ml-auto h-6 w-20" label={`${humanize(s)} over time: ${values.join(", ")}`} />
            </li>
          );
        })}
      </ul>
      <p className="mt-4 border-t border-divider pt-3 text-sm text-ink">
        <span className="font-semibold">Focus next: {humanize(focus).toLowerCase()}.</span>{" "}
        <span className="text-ink-secondary">{latest.rubric?.[focus]}</span>
      </p>
    </section>
  );
}

function Change({ value, digits }: { value: number; digits: number }) {
  const shown = value.toFixed(digits);
  if (Number(shown) === 0) return <span className="w-12 text-sm text-ink-secondary">no change</span>;
  return (
    <span className="w-12 text-sm text-ink-secondary tabular-nums" aria-label={`${value > 0 ? "up" : "down"} ${Math.abs(Number(shown))} since your first mock`}>
      {value > 0 ? "▲" : "▼"} {Math.abs(Number(shown))}
    </span>
  );
}

function Spark({ values, min, max, className, label }: { values: number[]; min: number; max: number; className: string; label: string }) {
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * 100},${30 - ((v - min) / (max - min)) * 28 - 1}`)
    .join(" ");
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label={label} className={`${className} text-primary`}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth={2} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}
