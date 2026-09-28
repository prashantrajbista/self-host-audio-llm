import { useEffect, useRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import type { Turn } from "@/lib/useVoiceSession";
import { Icon } from "./CallControls";

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

// Bottom sheet on a native <dialog>: Esc-to-close, focus trap and backdrop come from the platform.
export function HistoryDrawer({ open, onClose, turns }: { open: boolean; onClose: () => void; turns: Turn[] }) {
  const ref = useRef<HTMLDialogElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ block: "end" });
  }, [open, turns]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      // the content wrapper fills the dialog, so a click whose target is the dialog itself hit the backdrop
      onClick={(e) => e.target === ref.current && onClose()}
      aria-label="Conversation history"
      className="mt-auto mb-0 mx-auto w-full max-w-full sm:max-w-lg p-0 rounded-t-[20px] bg-surface shadow-ambient backdrop:bg-black/30 motion-safe:open:animate-slide-up"
    >
      <div className="flex flex-col max-h-[75dvh] font-sans">
        <header className="flex items-center justify-between px-5 py-4 border-b border-divider">
          <h2 className="text-[1.25rem] font-semibold text-ink">Conversation</h2>
          <button
            onClick={onClose}
            aria-label="Close history"
            className="size-9 rounded-full flex items-center justify-center text-ink-secondary hover:bg-divider/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
          >
            <Icon>
              <path d="M6 6l12 12M18 6L6 18" />
            </Icon>
          </button>
        </header>
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
      </div>
    </dialog>
  );
}
