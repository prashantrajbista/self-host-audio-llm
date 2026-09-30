import type { Metadata } from "next";
import { ScaledCard } from "@/components/ScaledCard";
import { cardTitle, fetchCard } from "@/lib/share";
import { PAGE, PRIMARY } from "@/lib/ui";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const card = await fetchCard((await params).slug);
  if (!card) return { title: "VoiceWire Interview", robots: { index: false } };
  const description = "Practice your interview with a live AI interviewer and get scored feedback.";
  // the opengraph-image file next to this page supplies the image
  return { title: cardTitle(card), description, openGraph: { title: cardTitle(card), description }, twitter: { card: "summary_large_image" } };
}

export default async function SharedResult({ params }: Props) {
  const { slug } = await params;
  const card = await fetchCard(slug);

  return (
    <main className={`${PAGE} flex flex-col items-center py-12`}>
      {card ? (
        <div className="w-full max-w-[720px] rounded-[14px] shadow-[0_24px_48px_-12px_rgba(0,0,0,0.18)]">
          <ScaledCard card={card} />
        </div>
      ) : (
        <p className="mt-10 text-ink-secondary">This result is no longer shared.</p>
      )}
      <div className="mt-12 max-w-md text-center">
        <h1 className="text-2xl font-bold text-ink text-balance">Practise your interview with a live AI interviewer</h1>
        <p className="mt-2 text-ink-secondary">Upload your CV, talk for about 15 minutes, and get scored feedback on every answer.</p>
        <a href="/" className={`${PRIMARY} mt-6 inline-block px-8 py-3`}>
          Take a free mock
        </a>
      </div>
    </main>
  );
}
