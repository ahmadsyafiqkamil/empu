"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/d/batik-tulis", label: "Dictionary", match: "/d" },
  { href: "/map", label: "Process map", match: "/map" },
  { href: "/evidence", label: "Evidence", match: "/evidence" },
  { href: "/try", label: "Try it", match: "/try" },
];

function isActive(pathname: string, match: string): boolean {
  if (match === "/d") return pathname.startsWith("/d");
  if (match === "/map") return pathname.startsWith("/map");
  return pathname.startsWith(match);
}

export function PublicHeader() {
  const pathname = usePathname() ?? "/";

  return (
    <header className="border-b-2 border-[var(--color-divider)] bg-[var(--color-bg)]">
      <div className="flex h-16 items-center gap-8 px-5 md:px-10">
        <Link
          href="/"
          className="font-heading mr-auto text-[22px] leading-none tracking-[-0.02em] text-[var(--color-text)] no-underline md:text-[24px]"
        >
          empu<span className="text-[var(--color-accent)]">.</span>
        </Link>

        <nav className="hidden items-center gap-7 text-sm lg:flex" aria-label="Main">
          {NAV.map((item) => {
            const on = isActive(pathname, item.match);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={on ? "page" : undefined}
                className={
                  on
                    ? "text-[var(--color-accent)] no-underline"
                    : "text-[var(--color-text)] no-underline hover:text-[var(--color-accent)]"
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <Link href="/studio" className="btn btn-secondary hidden lg:inline-flex">
          Documenter studio
        </Link>

        <details className="relative lg:hidden">
          <summary className="btn btn-secondary cursor-pointer list-none">Menu</summary>
          <div className="absolute right-0 top-12 z-40 w-56 border-2 border-[var(--color-text)] bg-[var(--color-bg)] shadow-[var(--shadow-md)]">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block px-4 py-2.5 text-sm text-[var(--color-text)] no-underline hover:bg-[var(--color-surface)]"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/studio"
              className="block border-t border-[var(--color-divider)] px-4 py-2.5 text-sm font-semibold text-[var(--color-text)] no-underline hover:bg-[var(--color-surface)]"
            >
              Documenter studio
            </Link>
          </div>
        </details>
      </div>
    </header>
  );
}
