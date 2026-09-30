import { PAGE, PRIMARY } from "@/lib/ui";

const STEPS = [
  { title: "Upload your CV", body: "Pick the role and level you're going for. Add the job post if you have it." },
  { title: "Interview by voice", body: "A live AI interviewer asks about your experience, follows up and lets you interrupt." },
  { title: "Get your report", body: "Scores per skill and question, how you spoke, and a stronger version of each answer." },
];

export default function Landing() {
  return (
    <main className={`${PAGE} flex flex-col items-center`}>
      <div className="w-full max-w-2xl py-12 text-center sm:py-20">
        <h1 className="text-4xl font-bold leading-tight text-ink sm:text-5xl">Practice interviews with a live AI interviewer</h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-ink-secondary">
          Upload your CV, talk for about 15 minutes, and get scored feedback on every answer.
        </p>
        <a href="/new" className={`${PRIMARY} mt-8 inline-block px-8 py-3`}>
          Start a free mock
        </a>
        <p className="mt-3 text-sm text-ink-secondary">Your first 2 mocks are free. Recordings are private to you.</p>
      </div>

      <ol className="grid w-full max-w-3xl gap-4 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step.title} className="rounded-[12px] border border-divider bg-surface p-5">
            <p className="text-sm font-semibold text-primary tabular-nums">Step {i + 1}</p>
            <p className="mt-1 font-semibold text-ink">{step.title}</p>
            <p className="mt-1 text-sm text-ink-secondary">{step.body}</p>
          </li>
        ))}
      </ol>

      <p className="mt-12 text-sm text-ink-secondary">
        Already practising?{" "}
        <a href="/history" className="text-link hover:underline">
          See your interviews
        </a>
      </p>
    </main>
  );
}
