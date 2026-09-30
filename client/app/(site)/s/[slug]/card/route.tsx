import { ImageResponse } from "next/og";
import { CARD_SIZES, ShareCard } from "@/components/ShareCard";
import { fetchCard } from "@/lib/share";

// Portrait card as a download, for posting as an image (LinkedIn, Instagram).
export async function GET(_req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const card = await fetchCard((await params).slug);
  if (!card) return new Response("Not found", { status: 404 });
  return new ImageResponse(<ShareCard card={card} layout="tall" />, {
    ...CARD_SIZES.tall,
    headers: { "Content-Disposition": 'attachment; filename="interview-result.png"', "Cache-Control": "no-store" },
  });
}
