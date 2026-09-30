import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  // absolute URLs for share-card images in link previews
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "Interview Coach",
  description: "Practice interviews with a live AI interviewer and get scored feedback.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
