import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public pages only; add new landing pages here.
const PATHS = ["", "/interview-warmup-alternative", "/behavioral-interview-practice", "/contact", "/privacy", "/terms"];

export default function sitemap(): MetadataRoute.Sitemap {
  return PATHS.map((p) => ({ url: `${SITE_URL}${p}` }));
}
