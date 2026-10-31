"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/studio", label: "Recordings" },
  { href: "/studio/upload", label: "Upload" },
  { href: "/studio/ask", label: "Ask" },
  { href: "/studio/export", label: "Export" },
  { href: "/studio/packs", label: "Craft packs" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/studio") {
    return pathname === "/studio" || pathname.startsWith("/studio/recordings");
  }
  return pathname.startsWith(href);
}

export function StudioHeader() {
  const pathname = usePathname() ?? "/studio";

  return (
    <header
      className="flex min-h-14 flex-wrap items-center gap-x-8 gap-y-2 px-6 py-3 text-[var(--color-bg)] md:flex-nowrap md:py-0"
      style={{ background: "var(--color-text)" }}
    >
      <Link href="/studio" className="flex items-baseline gap-2 no-underline">
        <span className="font-heading text-xl leading-none tracking-[-0.02em] text-[var(--color-bg)]">
          empu<span className="text-[var(--color-accent)]">.</span>
        </span>
        <span className="text-sm text-[var(--color-bg)]/70">Studio</span>
      </Link>

      <nav className="mr-auto flex flex-wrap items-center gap-6 text-sm" aria-label="Studio">
        {NAV.map((item) => {
          const on = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={on ? "page" : undefined}
              className={
                on
                  ? "border-b-2 border-[var(--color-accent)] pb-0.5 text-[var(--color-bg)] no-underline"
                  : "text-[var(--color-bg)]/75 no-underline hover:text-[var(--color-bg)]"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <Link
        href="/"
        className="text-sm text-[var(--color-bg)]/75 no-underline hover:text-[var(--color-bg)]"
      >
        Public site ↗
      </Link>
    </header>
  );
}
