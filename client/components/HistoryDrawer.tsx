import { useEffect, useRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import type { Turn } from "@/lib/useVoiceSession";
import { Sheet } from "./Sheet";

// Tailwind's preflight strips default heading/list styling, so headings/bold/lists would
// otherwise render visually identical to plain text — these give them back their shape.
const components: Components = {
  h1: ({ children }) => <h1 className="text-[1.375rem] font-bold mb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-[1.25rem] font-semibold mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-[1.25rem] font-semibold mb-1">{children}</h3>,
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => <ul className="list-disc list-inside">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside">{children}</ol>,
  code: ({ children }) => <code className="bg-divider/50 text-ink px-1 rounded">{children}</code>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="underline text-link">
      {children}
    </a>
  ),
};

export function HistoryDrawer({ open, onClose, turns }: { open: boolean; onClose: () => void; turns: Turn[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ block: "end" });
  }, [open, turns]);

  return (
    <Sheet open={open} onClose={onClose} title="Conversation">
      <div className="overflow-y-auto px-5 py-4 flex flex-col gap-3 text-[1.0625rem] leading-relaxed text-ink">
        {turns.length === 0 ? (
          <p className="text-ink-secondary text-center py-8">Nothing yet — start talking.</p>
        ) : (
          turns.map((turn, i) =>
            turn.role === "user" ? (
              <div key={i} className="self-end max-w-[85%] rounded-2xl rounded-br-md bg-bg px-4 py-2">
                {turn.text}
              </div>
            ) : (
              <div key={i} className="self-start max-w-[85%] rounded-2xl rounded-bl-md border border-divider px-4 py-2">
                <ReactMarkdown components={components}>{turn.text}</ReactMarkdown>
              </div>
            ),
          )
        )}
        <div ref={endRef} />
      </div>
    </Sheet>
  );
}
