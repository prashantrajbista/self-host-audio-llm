import type { Metadata } from "next";
import "./globals.css";
import { THEME_SCRIPT } from "@/lib/theme";
import { BRAND, SITE_URL, TAGLINE } from "@/lib/site";

export const metadata: Metadata = {
  // absolute URLs for share-card images in link previews
  metadataBase: new URL(SITE_URL),
  title: "AI Mock Interview by Voice, Free & Private | VoiceWire",
  description:
    "Practice out loud with a live AI interviewer that asks about your CV and scores every answer. CV anonymized, voice disguised, no subscription.",
  applicationName: BRAND,
  openGraph: { type: "website", siteName: BRAND, title: BRAND, description: TAGLINE },
  twitter: { card: "summary_large_image" },
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
