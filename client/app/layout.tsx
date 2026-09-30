import type { Metadata } from "next";
import "./globals.css";
import { THEME_SCRIPT } from "@/lib/theme";

export const metadata: Metadata = {
  // absolute URLs for share-card images in link previews
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "VoiceWire Interview: practise interviews with a live AI interviewer",
  description: "Practice interviews with a live AI interviewer and get scored feedback.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // suppressHydrationWarning: the theme script sets data-theme on <html> before React hydrates
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* runs before first paint, so a saved theme never flashes the other one */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
