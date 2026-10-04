import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Signed-in app screens hold nothing worth indexing.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/history", "/new", "/report/", "/interview/", "/login", "/demo"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
