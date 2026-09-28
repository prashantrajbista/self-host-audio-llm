import ReactMarkdown, { type Components } from "react-markdown";

// Tailwind's preflight strips default heading/list styling, so headings/bold/lists would
// otherwise render visually identical to plain text — these give them back their shape.
const components: Components = {
  h1: ({ children }) => <h1 className="text-[1.375rem] font-bold mb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-[1.25rem] font-semibold mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-[1.25rem] font-semibold mb-1">{children}</h3>,
  p: ({ children }) => <p className="mb-2">{children}</p>,
  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => <ul className="list-disc list-inside text-left">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside text-left">{children}</ol>,
  code: ({ children }) => <code className="bg-divider/50 text-ink px-1 rounded">{children}</code>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="underline text-link">
      {children}
    </a>
  ),
};

export function Transcript({ text }: { text: string }) {
  return (
    <div className="max-w-md min-h-[2.5em] text-center text-ink text-[1.0625rem] leading-relaxed">
      <ReactMarkdown components={components}>{text}</ReactMarkdown>
    </div>
  );
}
