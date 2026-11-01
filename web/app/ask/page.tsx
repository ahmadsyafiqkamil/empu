import { AskPanel } from "@/components/AskPanel";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { askSuggestionsAcross, type ArchiveTerms } from "@/lib/ask";
import { COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

async function termsFor(slug: string): Promise<string[]> {
  return fetch(`${API}/api/public/archives/${slug}/entries`, { cache: "no-store" })
    .then((r) => (r.ok ? (r.json() as Promise<EntryListItem[]>) : []))
    .then((rows) => rows.map((row) => row.term))
    .catch(() => [] as string[]);
}

export default async function AskPage() {
  const archives: Archive[] = await fetch(`${API}/api/public/archives`, { cache: "no-store" })
    .then((r) => (r.ok ? (r.json() as Promise<Archive[]>) : []))
    .catch(() => [] as Archive[]);

  const groups: ArchiveTerms[] = await Promise.all(
    archives.map(async (archive) => ({
      title: archive.title,
      terms: await termsFor(archive.slug),
    })),
  );

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[900px] px-5 pt-7 pb-16 lg:px-0 lg:pt-8">
        <p className="text-[13px] text-[var(--color-neutral-700)]">Home / Ask</p>

        <div className="mt-4 border-b-2 border-[var(--color-divider)] pb-6">
          <h1 className="text-[34px] leading-none tracking-[-0.03em] md:text-[44px] lg:text-[52px]">
            {COPY.ask.title}
          </h1>
          <p className="mt-3 max-w-[620px] text-[15px] text-[var(--color-neutral-800)]">
            {COPY.ask.intro}
          </p>
        </div>

        <div className="pt-6">
          <AskPanel endpoint="/api/public/ask" suggestions={askSuggestionsAcross(groups)} />
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
