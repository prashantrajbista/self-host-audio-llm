import ReactMarkdown, { type Components } from "react-markdown";

// Tailwind's preflight strips default heading/list styling, so headings/bold/lists would
// otherwise render visually identical to plain text — these give them back their shape.
const components: Components = {
  h1: ({ children }) => <h1 className="text-2xl font-bold mb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-xl font-bold mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-lg font-bold mb-1">{children}</h3>,
  p: ({ children }) => <p className="mb-2">{children}</p>,
  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => <ul className="list-disc list-inside text-left">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside text-left">{children}</ol>,
  code: ({ children }) => <code className="bg-gray-800 px-1 rounded">{children}</code>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="underline text-blue-400">
      {children}
    </a>
  ),
};

export function Transcript({ text }: { text: string }) {
  return (
    <div className="max-w-md min-h-[2.5em] text-center text-gray-200 text-lg leading-relaxed">
      <ReactMarkdown components={components}>{text}</ReactMarkdown>
    </div>
  );
}
