import Link from "next/link";
import { ClearFiltersButton, DictionaryFilters } from "@/components/DictionaryFilters";
import { EntryRow } from "@/components/EntryRow";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { CATEGORY_LABEL, COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";
const ORDER = ["tool", "tool_part", "material", "dye", "stage", "technique", "motif", "other"];

export const dynamic = "force-dynamic";

type Pack = {
  id: string;
  version: string;
  name: { id: string; en: string };
  stages: { id: string; label: { id: string; en: string } }[];
};

function groupByCategory(items: EntryListItem[]): [string, EntryListItem[]][] {
  const groups = new Map<string, EntryListItem[]>();
  for (const e of items) {
    const key = e.category || "other";
    const list = groups.get(key) ?? [];
    list.push(e);
    groups.set(key, list);
  }
  return [...groups.entries()].sort((a, b) => ORDER.indexOf(a[0]) - ORDER.indexOf(b[0]));
}

export default async function DictionaryPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ q?: string; category?: string; stage?: string; is_novel?: string }>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const q = sp.q ?? "";
  const category = sp.category ?? "";
  const stage = sp.stage ?? "";
  const isNovel = sp.is_novel === "1";

  const archive: Archive | null = await fetch(`${API}/api/public/archives/${slug}`, {
    cache: "no-store",
  }).then((r) => (r.ok ? r.json() : null));

  if (!archive) {
    return (
      <>
        <PublicHeader />
        <main className="mx-auto w-full max-w-[1100px] px-5 py-16 lg:px-0">
          <div className="empty">
            <span>{COPY.empty.dictionary}</span>
            <Link href="/evidence" className="btn btn-secondary">
              {COPY.home.seeEvidence}
            </Link>
          </div>
        </main>
        <PublicFooter />
      </>
    );
  }

  const pack: Pack | null = await fetch(`${API}/api/packs/${archive.craft_pack_id}`, {
    cache: "no-store",
  })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  const qs = new URLSearchParams();
  if (q) qs.set("q", q);
  if (category) qs.set("category", category);
  if (stage) qs.set("stage", stage);
  if (isNovel) qs.set("is_novel", "1");

  const entries: EntryListItem[] = await fetch(
    `${API}/api/public/archives/${slug}/entries?${qs}`,
    { cache: "no-store" },
  ).then((r) => (r.ok ? r.json() : []));

  const groups = groupByCategory(entries);
  const stages = (pack?.stages ?? []).map((s) => ({
    id: s.id,
    label: s.label?.en ? `${s.id} · ${s.label.en}` : s.id,
  }));

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[1100px] px-5 pt-7 pb-16 lg:px-0 lg:pt-8">
        <p className="text-[13px] text-[var(--color-neutral-700)]">
          <Link href="/" className="text-inherit">
            Home
          </Link>{" "}
          / Living Archive
        </p>

        <div className="grid grid-cols-[minmax(0,1fr)] items-end gap-4 border-b-2 border-[var(--color-divider)] pt-4 pb-6 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div>
            <h1 className="text-[34px] leading-none tracking-[-0.03em] md:text-[44px] lg:text-[56px]">
              {archive.title}
            </h1>
            <p className="mt-2 text-[13px] text-[var(--color-neutral-800)] md:text-[14px]">
              {archive.validated_count} validated terms · {archive.recording_count} recordings
              {pack ? ` · ${pack.id} v${pack.version}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/d/${slug}/ask`} className="btn btn-secondary h-10">
              {COPY.ask.askArchive}
            </Link>
            <Link href="/map" className="btn btn-secondary h-10">
              {COPY.ui.processMap}
            </Link>
            <a
              href={`/api/archives/${archive.id}/export?format=zip&scope=public`}
              className="btn btn-primary h-10 gap-2"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden
              >
                <path d="M12 15V3M7 10l5 5 5-5M21 21H3" />
              </svg>
              {COPY.ui.downloadPublic}
            </a>
          </div>
        </div>

        <DictionaryFilters
          stages={stages}
          q={q}
          category={category}
          stage={stage}
          isNovel={isNovel}
        />

        {entries.length === 0 ? (
          <div className="empty mt-8">
            <span>{COPY.ui.noTerms}</span>
            <ClearFiltersButton />
          </div>
        ) : (
          groups.map(([cat, items]) => (
            <section key={cat} className="pt-8">
              <div className="flex items-baseline justify-between border-b-2 border-[var(--color-divider)] pb-2">
                <h3 className="m-0 text-[20px] tracking-[-0.01em] lg:text-[24px]">
                  {CATEGORY_LABEL[cat] ?? cat}
                </h3>
                <span className="text-[13px] text-[var(--color-neutral-700)]">
                  {items.length} terms
                </span>
              </div>
              <div className="md:grid md:grid-cols-3">
                {items.map((e) => (
                  <EntryRow key={e.id} slug={slug} e={e} />
                ))}
              </div>
            </section>
          ))
        )}
      </main>
      <PublicFooter />
    </>
  );
}
