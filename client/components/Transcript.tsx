export function Transcript({ text }: { text: string }) {
  return (
    <div className="max-w-md min-h-[2.5em] text-center text-gray-200 text-lg leading-relaxed">
      {text}
    </div>
  );
}
