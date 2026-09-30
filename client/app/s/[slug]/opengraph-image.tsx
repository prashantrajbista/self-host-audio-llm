import { ImageResponse } from "next/og";
import { CARD_SIZES, ShareCard } from "@/components/ShareCard";
import { fetchCard } from "@/lib/share";

export const alt = "Mock interview result";
export const size = CARD_SIZES.wide;
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const card = await fetchCard((await params).slug);
  if (!card) return new Response("Not found", { status: 404 });
  return new ImageResponse(<ShareCard card={card} layout="wide" />, size);
}
