import { HeaderAuthLinks } from "@/components/AuthAware";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BRAND, OPERATOR } from "@/lib/site";

export function SiteHeader() {
  return (
    <header className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4">
      <a href="/" className="font-semibold text-ink hover:text-primary">
        {BRAND}
      </a>
      <nav aria-label="Main" className="flex items-center gap-5 text-sm">
        <a href="/#pricing" className="text-ink-secondary hover:text-ink">
          Pricing
        </a>
        <a href="/#faq" className="hidden text-ink-secondary hover:text-ink sm:inline">
          FAQ
        </a>
        <ThemeToggle />
        <HeaderAuthLinks />
      </nav>
    </header>
  );
}

const LINKS = [
  { href: "/#pricing", label: "Pricing" },
  { href: "/interview-warmup-alternative", label: "Interview Warmup alternative" },
  { href: "/terms", label: "Terms" },
  { href: "/privacy", label: "Privacy" },
  { href: "/contact", label: "Contact" },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-divider">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-8 text-sm text-ink-secondary sm:flex-row sm:items-center sm:justify-between">
        <p>
          © {new Date().getFullYear()} {OPERATOR}. Practice interviews, privately.
        </p>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  );
}
