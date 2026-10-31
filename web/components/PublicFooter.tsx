import Link from "next/link";
import { COPY } from "@/lib/copy";

export function PublicFooter() {
  return (
    <footer className="border-t-2 border-[var(--color-divider)] px-5 py-8 md:px-10">
      <div className="grid grid-cols-[minmax(0,1fr)] gap-8 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-2 text-xs text-[var(--color-neutral-800)]">
          <span>{COPY.home.frameAttribution}</span>
          <span>{COPY.footer}</span>
        </div>
        <div className="flex gap-6 text-[13px] md:justify-end">
          <Link href="/evidence">Evidence</Link>
          <Link href="/studio">Documenter studio</Link>
        </div>
      </div>
    </footer>
  );
}
