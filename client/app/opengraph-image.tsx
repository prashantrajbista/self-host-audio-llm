import { ImageResponse } from "next/og";
import { BRAND, TAGLINE } from "@/lib/site";

// Default link-preview card for every page without its own (shared results have one under s/[slug]).
export const alt = BRAND;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", padding: 80, background: "#111827", color: "#fff" }}>
        <div style={{ fontSize: 72, fontWeight: 700 }}>{BRAND}</div>
        <div style={{ fontSize: 36, marginTop: 24, color: "#d1d5db" }}>{TAGLINE}</div>
      </div>
    ),
    size,
  );
}
