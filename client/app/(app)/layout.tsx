import { AppHeader } from "@/components/AppHeader";
import { SiteFooter } from "@/components/SiteChrome";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg font-sans">
      <AppHeader />
      <div className="flex-1">{children}</div>
      <SiteFooter />
    </div>
  );
}
