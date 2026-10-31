import Link from "next/link";
import { AskPanel } from "@/components/AskPanel";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { askSuggestions } from "@/lib/ask";
import { COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export default async function AskPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  const archive: Archive | null = await fetch(`${API}/api/public/archives/${slug}`, {
    cache: "no-store",
  })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  const entries: EntryListItem[] = archive
    ? await fetch(`${API}/api/public/archives/${slug}/entries`, { cache: "no-store" })
        .then((r) => (r.ok ? (r.json() as Promise<EntryListItem[]>) : []))
        .catch(() => [] as EntryListItem[])
    : [];

  if (!archive) {
    return (
      <>
        <PublicHeader />
        <main className="mx-auto w-full max-w-[900px] px-5 py-16 lg:px-0">
          <div className="empty">
            <span>{COPY.empty.entry404}</span>
            <Link href="/" className="btn btn-secondary">
              Home
            </Link>
          </div>
        </main>
        <PublicFooter />
      </>
    );
  }

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[900px] px-5 pt-7 pb-16 lg:px-0 lg:pt-8">
        <p className="text-[13px] text-[var(--color-neutral-700)]">
          <Link href="/" className="text-inherit">
            Home
          </Link>{" "}
          /{" "}
          <Link href={`/d/${slug}`} className="text-inherit">
            {archive.title}
          </Link>
        </p>

        <div className="mt-4 border-b-2 border-[var(--color-divider)] pb-6">
          <h1 className="text-[34px] leading-none tracking-[-0.03em] md:text-[44px] lg:text-[52px]">
            {COPY.ask.title}
          </h1>
          <p className="mt-3 max-w-[620px] text-[15px] text-[var(--color-neutral-800)]">
            {COPY.ask.intro}
          </p>
        </div>

        <div className="pt-6">
          <AskPanel
            endpoint={`/api/public/archives/${slug}/ask`}
            slug={slug}
            suggestions={askSuggestions(entries)}
          />
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
