import Link from "next/link";
import { EntryCardPublic } from "@/components/EntryCardPublic";
import { EntryRow } from "@/components/EntryRow";
import { CATEGORY_LABEL, COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

type Pack = {
  id: string;
  version: string;
  stages: { id: string; label: { id: string; en: string } }[];
};

const CATEGORIES = ["tool", "tool_part", "material", "dye", "stage", "technique", "motif", "other"];

function groupByLetter(items: EntryListItem[]): [string, EntryListItem[]][] {
  const groups = new Map<string, EntryListItem[]>();
  for (const e of items) {
    const letter = (e.term[0] ?? "#").toUpperCase();
    const list = groups.get(letter) ?? [];
    list.push(e);
    groups.set(letter, list);
  }
  return [...groups.entries()];
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

  const archive: Archive = await fetch(`${API}/api/public/archives/${slug}`, {
    cache: "no-store",
  }).then((r) => (r.ok ? r.json() : null));
  if (!archive) {
    return <p className="p-8">{COPY.empty.entry404}</p>;
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

  function chipQuery(overrides: Record<string, string>) {
    const next = new URLSearchParams(qs);
    for (const [k, v] of Object.entries(overrides)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    const s = next.toString();
    return s ? `?${s}` : "";
  }

  const groups = groupByLetter(entries);

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <header className="space-y-2 border-b border-[var(--line)] pb-6">
        <p className="text-sm text-[var(--muted)]">
          <Link href="/" className="underline">
            Home
          </Link>{" "}
          · Living Archive
        </p>
        <h1 className="font-display text-3xl">{archive.title} · Batik Tulis</h1>
        <p className="text-sm text-[var(--muted)]">
          {archive.validated_count} validated terms · {archive.recording_count} recordings
          {pack ? ` · batik_tulis v${pack.version}` : ""}
        </p>
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href={`/api/archives/${archive.id}/export?format=zip&scope=public`} className="underline">
            Download (ZIP)
          </Link>
        </div>
      </header>

      <form className="mt-6 flex flex-wrap items-center gap-2" method="get">
        {category ? <input type="hidden" name="category" value={category} /> : null}
        {stage ? <input type="hidden" name="stage" value={stage} /> : null}
        {isNovel ? <input type="hidden" name="is_novel" value="1" /> : null}
        <input
          name="q"
          defaultValue={q}
          placeholder="Search terms"
          className="min-w-0 flex-1 border border-[var(--line)] bg-transparent px-3 py-2"
        />
        <button className="border border-[var(--line)] px-4 py-2">Search</button>
      </form>

      <div className="mt-4 flex flex-wrap gap-2 text-sm">
        <Link
          href={chipQuery({ category: "" })}
          className={`border px-3 py-1 ${category ? "border-[var(--line)]" : "bg-[var(--accent)] text-white"}`}
        >
          All
        </Link>
        {CATEGORIES.map((c) => (
          <Link
            key={c}
            href={chipQuery({ category: category === c ? "" : c })}
            className={`border px-3 py-1 ${category === c ? "bg-[var(--accent)] text-white" : "border-[var(--line)]"}`}
          >
            {CATEGORY_LABEL[c]}
          </Link>
        ))}
        <Link
          href={chipQuery({ is_novel: isNovel ? "" : "1" })}
          className={`border px-3 py-1 ${isNovel ? "bg-[var(--accent)] text-white" : "border-[var(--line)]"}`}
        >
          New terms only
        </Link>
      </div>

      {pack && pack.stages?.length ? (
        <form className="mt-4 flex items-center gap-2 text-sm" method="get">
          {q ? <input type="hidden" name="q" value={q} /> : null}
          {category ? <input type="hidden" name="category" value={category} /> : null}
          {isNovel ? <input type="hidden" name="is_novel" value="1" /> : null}
          <label htmlFor="stage" className="text-[var(--muted)]">
            Stage
          </label>
          <select
            id="stage"
            name="stage"
            defaultValue={stage}
            className="border border-[var(--line)] bg-transparent px-2 py-1"
          >
            <option value="">All stages</option>
            {pack.stages.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id}
              </option>
            ))}
          </select>
          <button className="border border-[var(--line)] px-3 py-1">Apply</button>
        </form>
      ) : null}

      {entries.length === 0 ? (
        <p className="mt-10 text-[var(--muted)]">{COPY.empty.dictionary}</p>
      ) : (
        <>
          {/* Mobile list */}
          <ul className="mt-6 divide-y divide-[var(--line)] md:hidden">
            {entries.map((e) => (
              <li key={e.id}>
                <EntryRow slug={slug} e={e} />
              </li>
            ))}
          </ul>

          {/* Desktop grid grouped A–Z */}
          <div className="mt-6 hidden md:block">
            {groups.map(([letter, items]) => (
              <section key={letter} className="mb-8">
                <h2 className="mb-2 border-b border-[var(--line)] font-mono text-sm text-[var(--muted)]">
                  {letter}
                </h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {items.map((e) => (
                    <EntryCardPublic key={e.id} slug={slug} e={e} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </>
      )}
    </main>
  );
}