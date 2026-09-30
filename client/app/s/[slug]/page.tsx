import type { Metadata } from "next";
import { ShareCard } from "@/components/ShareCard";
import { cardTitle, fetchCard } from "@/lib/share";
import { PAGE, PRIMARY } from "@/lib/ui";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const card = await fetchCard((await params).slug);
  if (!card) return { title: "Interview Coach", robots: { index: false } };
  const description = "Practice your interview with a live AI interviewer and get scored feedback.";
  // the opengraph-image file next to this page supplies the image
  return { title: cardTitle(card), description, openGraph: { title: cardTitle(card), description }, twitter: { card: "summary_large_image" } };
}

export default async function SharedResult({ params }: Props) {
  const { slug } = await params;
  const card = await fetchCard(slug);

  return (
    <main className={`${PAGE} flex flex-col items-center`}>
      {card ? (
        <div className="w-full max-w-[600px] overflow-hidden rounded-[12px] border border-divider shadow-ambient">
          {/* the fixed 1200x630 card, scaled to fit the column */}
          <div className="relative w-full" style={{ aspectRatio: "1200 / 630" }}>
            <div className="absolute left-0 top-0 origin-top-left" style={{ transform: "scale(0.5)" }}>
              <ShareCard card={card} layout="wide" />
            </div>
          </div>
        </div>
      ) : (
        <p className="mt-10 text-ink-secondary">This result is no longer shared.</p>
      )}
      <div className="mt-10 max-w-md text-center">
        <h1 className="text-2xl font-bold text-ink">Practice your interview with a live AI interviewer</h1>
        <p className="mt-2 text-ink-secondary">Upload your CV, talk for about 15 minutes, and get scored feedback on every answer.</p>
        <a href="/" className={`${PRIMARY} mt-6 inline-block px-8 py-3`}>
          Take a free mock
        </a>
      </div>
    </main>
  );
}
