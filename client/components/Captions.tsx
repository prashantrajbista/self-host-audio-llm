import type { SessionState, Turn } from "@/lib/useVoiceSession";

// Live caption under the orb: your last utterance while it works on a reply, then the reply as it
// streams. Fixed two-line window anchored to the bottom, so the newest words stay visible and older
// ones fade out the top. Full history lives in the drawer.
export function Captions({ turns, state, hint }: { turns: Turn[]; state: SessionState; hint: string | null }) {
  const last = turns[turns.length - 1];
  let text: string | null = null;
  let secondary = false;

  if (!last) {
    if (hint) {
      text = `Try saying: “${hint}”`;
      secondary = true;
    }
  } else if (last.role === "user") {
    text = `You: ${last.text}`;
    secondary = true;
  } else if (state !== "listening") {
    // user is talking again: the previous reply is stale until their new transcript lands
    text = last.text;
  }

  return (
    <div className="h-[3.25em] w-full max-w-md overflow-hidden flex flex-col justify-end text-center text-[1.0625rem] leading-relaxed [mask-image:linear-gradient(to_bottom,transparent,black_45%)]">
      {text && <p className={secondary ? "text-ink-secondary" : "text-ink"}>{text}</p>}
    </div>
  );
}
